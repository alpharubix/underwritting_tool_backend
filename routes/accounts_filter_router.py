import calendar
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, Request

accounts_filter_router = APIRouter(prefix="/v1/crm", tags=["accounts-filter"])


def parse_date(date_str: str, is_end: bool = False):

    if not date_str:
        return None

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if is_end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError:
        pass

    try:
        dt = datetime.strptime(date_str, "%Y-%m")
        if is_end:
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            dt = dt.replace(
                day=last_day, hour=23, minute=59, second=59, microsecond=999999
            )
        return dt
    except ValueError:
        pass

    try:
        dt = datetime.fromisoformat(date_str)
        if is_end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError:
        return None


MODULE_CONFIG = {
    "bsa": {
        "collection": "bsa_merged_bankstatements",
        "fields": ["user_id", "from_date", "to_date", "created_at"],
        "period_from_field": "from_date",
        "period_to_field": "to_date",
        "period_type": "date",  # real Mongo Date, e.g. 2025-08-01T00:00:00Z
        "created_at_field": "created_at",
    },
    "gst": {
        "collection": "gst_reference",
        "fields": [
            "user_id",
            "reference_id",
            "gstin",
            "from_month",
            "to_month",
            "webhook_received_time",
        ],
        "period_from_field": "from_month",
        "period_to_field": "to_month",
        "period_type": "month_string",  # 'MMYYYY' string, e.g. "012025"
        "created_at_field": "webhook_received_time",
    },
    "itr": {
        "collection": "itr_analyzed_report",
        "fields": [
            "user_id",
            "reference_id",
            "created_at",
        ],
        "period_from_field": None,  # from_date/to_date intentionally not applied to itr
        "period_to_field": None,
        "period_type": None,
        "created_at_field": "created_at",
    },
    "cibil": {
        "collection": "cibil_report",
        "fields": ["user_id", "reference_id", "score", "created_at"],
        "period_from_field": None,  # cibil has no period concept
        "period_to_field": None,
        "period_type": None,
        "created_at_field": "created_at",
    },
}


def build_period_match(config: dict, from_date: datetime, to_date: datetime) -> dict:

    period_from_field = config["period_from_field"]
    period_to_field = config["period_to_field"]
    period_type = config["period_type"]

    if not period_from_field or not period_to_field or not from_date or not to_date:
        return {}

    if period_type == "date":
        return {
            period_from_field: {"$gte": from_date},
            period_to_field: {"$lte": to_date},
        }

    if period_type == "year":
        return {
            period_from_field: {"$gte": from_date.year},
            period_to_field: {"$lte": to_date.year},
        }

    if period_type == "month_string":
        from_key = f"{from_date.year}{from_date.month:02d}"
        to_key = f"{to_date.year}{to_date.month:02d}"

        def _as_yyyymm(field: str) -> dict:
            return {
                "$concat": [
                    {"$substrCP": [f"${field}", 2, 4]},  # YYYY
                    {"$substrCP": [f"${field}", 0, 2]},  # MM
                ]
            }

        return {
            "$expr": {
                "$and": [
                    {"$gte": [_as_yyyymm(period_from_field), from_key]},
                    {"$lte": [_as_yyyymm(period_to_field), to_key]},
                ]
            }
        }

    return {}


@accounts_filter_router.get("/accounts-filter")
async def get_accounts_filter(
    request: Request,
    module: str = Query(...),
    created_at: str = Query(None),
    from_date: str = Query(None),
    to_date: str = Query(None),
):
    db = request.app.state.mongo_db
    module_key = module.lower()

    if module_key not in MODULE_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unsupported module: {module}")

    config = MODULE_CONFIG[module_key]
    collection = db[config["collection"]]

    query: dict = {}

    # --- created_at filter (single day) ---
    parsed_created_at = parse_date(created_at)
    if parsed_created_at:
        created_field = config["created_at_field"]
        query[created_field] = {
            "$gte": parsed_created_at.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            "$lte": parsed_created_at.replace(
                hour=23, minute=59, second=59, microsecond=999999
            ),
        }

    # --- period filter: ONE call covers bsa / gst / itr; cibil returns {} ---
    # from_date=2025-01&to_date=2025-12 -> Jan 2025 through the last day of Dec 2025
    parsed_from = parse_date(from_date)
    parsed_to = parse_date(to_date, is_end=True)
    query.update(build_period_match(config, parsed_from, parsed_to))

    # --- projection ---
    projection = {field: 1 for field in config["fields"]}
    if module_key == "cibil":
        del projection["score"]
        projection["cibil_report.EquifaxRetail.BureauAnalysis.score"] = 1
    elif module_key == "bsa":
        projection["account_details.Account Number"] = 1
        projection["account_details.Account Type"] = 1
    projection["_id"] = 0

    documents = await collection.find(query, projection).to_list(length=None)

    # --- resolve account_ids ---
    user_ids = list({doc.get("user_id") for doc in documents if doc.get("user_id")})
    valid_object_ids = []
    for uid in user_ids:
        try:
            valid_object_ids.append(ObjectId(uid))
        except InvalidId:
            pass

    user_account_map = {}
    if valid_object_ids:
        users = (
            await db["users"]
            .find({"_id": {"$in": valid_object_ids}}, {"account_id": 1})
            .to_list(length=None)
        )
        user_account_map = {str(u["_id"]): u.get("account_id") for u in users}

    response_data = []
    for doc in documents:
        user_id = doc.get("user_id")
        formatted_doc = {"account_id": user_account_map.get(user_id)}
        for field in config["fields"]:
            if module_key == "cibil" and field == "score":
                formatted_doc["score"] = (
                    doc.get("cibil_report", {})
                    .get("EquifaxRetail", {})
                    .get("BureauAnalysis", {})
                    .get("score")
                )
            elif module_key == "gst" and field == "webhook_received_time":
                formatted_doc["created_at"] = doc.get("webhook_received_time")
            else:
                formatted_doc[field] = doc.get(field)

        if module_key == "bsa":
            account_details = doc.get("account_details", {})
            formatted_doc["account_number"] = account_details.get("Account Number")
            formatted_doc["account_type"] = account_details.get("Account Type")

        response_data.append(formatted_doc)

    return {"message": "success", "data": response_data}


@accounts_filter_router.get("/accounts-filter/{account_id}")
async def get_all_modules_by_account_id(
    account_id: str,
    request: Request,
):
    db = request.app.state.mongo_db

    account_id_int = None
    try:
        account_id_int = int(account_id)
    except ValueError:
        pass

    query_cond = [{"account_id": account_id}]
    if account_id_int is not None:
        query_cond.append({"account_id": account_id_int})

    user = await db["users"].find_one({"$or": query_cond})

    if not user:
        raise HTTPException(
            status_code=404, detail=f"User with account_id {account_id} not found"
        )

    user_id = str(user["_id"])

    response_data = {}

    for module_key, config in MODULE_CONFIG.items():
        collection = db[config["collection"]]

        projection = {field: 1 for field in config["fields"]}
        if module_key == "cibil":
            if "score" in projection:
                del projection["score"]
            projection["cibil_report.EquifaxRetail.BureauAnalysis.score"] = 1
        elif module_key == "bsa":
            projection["account_details.Account Number"] = 1
            projection["account_details.Account Type"] = 1
        projection["_id"] = 0

        documents = await collection.find(
            {"user_id": user_id}, projection
        ).to_list(length=None)

        formatted_docs = []
        for doc in documents:
            formatted_doc = {"account_id": user.get("account_id")}
            for field in config["fields"]:
                if module_key == "cibil" and field == "score":
                    formatted_doc["score"] = (
                        doc.get("cibil_report", {})
                        .get("EquifaxRetail", {})
                        .get("BureauAnalysis", {})
                        .get("score")
                    )
                elif module_key == "gst" and field == "webhook_received_time":
                    formatted_doc["created_at"] = doc.get("webhook_received_time")
                else:
                    formatted_doc[field] = doc.get(field)

            if module_key == "bsa":
                account_details = doc.get("account_details", {})
                formatted_doc["account_number"] = account_details.get("Account Number")
                formatted_doc["account_type"] = account_details.get("Account Type")

            formatted_docs.append(formatted_doc)

        response_data[module_key] = formatted_docs

    return {"message": "success", "data": response_data}
