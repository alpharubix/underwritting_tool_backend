import logging
import time
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from starlette import status
from datetime import datetime



logger=logging.getLogger(__name__)

def normalize_date_range(from_date: datetime, to_date: datetime):
            normalized_from = from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            normalized_to   = to_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return normalized_from, normalized_to


async def bsa_summary_of_debit_credit_monthwise(db,user_id:str,from_date,to_date):
    logger.info("Bank Statement Summary of Debit and Credit | user_id=%s ",user_id)
    start_time=time.perf_counter()

    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid user_id"}
        )
    if not isinstance(from_date, datetime) or not isinstance(to_date, datetime):
        raise HTTPException(
            status_code=400,
            detail={"message": "Internal error: from_date and to_date must be datetime objects"}
        )
    normalized_from, normalized_to = normalize_date_range(from_date, to_date)
    logger.info("Normalized date range | from=%s | to=%s", normalized_from, normalized_to)

    # try:
    #     exists = await db.bankstatementreport.find_one({"user_id": str(user_id)}, {"_id": 1})
    # except Exception as e:
    #     logger.error("preflight_failed | user_id=%s | error=%s", user_id, str(e), exc_info=True)
    #     raise HTTPException(
    #         status_code=500,
    #         detail={"message": "Database error during preflight check"}
    #     )

    # if not exists:
    #     logger.warning("report_not_found | user_id=%s", user_id)
    #     raise HTTPException(
    #         status_code=404,
    #         detail={"message": "Bank Statement Report not found for this user"}
    #     )
    
    try:
        # docs_count=await db.bankstatementreport.count_documents({"user_id":str(user_id)})
        # logger.info("Bank_statement_report |user_id=%s |docs_counts=%s",user_id,docs_count)
        

        

        pipeline = [
            # 1. Match by user_id
            {
                "$match": {
                    "user_id": user_id
                }
            },

            # 2. Early projection — drop heavy fields before unwind
            {
                "$project": {
                    "user_id": 1,
                    "created_at": 1,
                    "analysis_metadata.Data.Summary Of Debit And Credit": 1
                }
            },

            # 3. Unwind
            {
                "$unwind": "$analysis_metadata.Data.Summary Of Debit And Credit"
            },

            # 4. Filter using stored parsedMonthDate (no conversion needed)
            {
                "$match": {
                    "analysis_metadata.Data.Summary Of Debit And Credit.parsedMonthDate": {
                        "$gte": normalized_from,
                        "$lte": normalized_to
                    }
                }
            },

            # 5. Deduplicate — latest document wins per month
            {
                "$sort": { "created_at": -1 }
            },
            {
                "$group": {
                    "_id": {
                        "user_id": "$user_id",
                        "month": "$analysis_metadata.Data.Summary Of Debit And Credit.month"
                    },
                    "parsedMonthDate":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.parsedMonthDate" },
                    "cashdeposit":      { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.cashdeposit" },
                    "chequeReceipt":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceipt" },
                    "onlineReceipt":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceipt" },
                    "otherRecipt":      { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.otherRecipt" },
                    "inhouseRecipt":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.inhouseRecipt" },
                    "cashdepositNo":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.cashdepositNo" },
                    "chequeReceiptNo":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceiptNo" },
                    "onlineReceiptNo":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceiptNo" },
                    "otherReciptNo":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.otherReciptNo" },
                    "inhouseReciptNo":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.inhouseReciptNo" },
                    "cashwithDraw":     { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDraw" },
                    "chequePayment":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.chequePayment" },
                    "onlinePayment":    { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.onlinePayment" },
                    "otherPayment":     { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.otherPayment" },
                    "inhousePayment":   { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.inhousePayment" },
                    "cashwithDrawNo":   { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDrawNo" },
                    "chequePaymentNo":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.chequePaymentNo" },
                    "onlinePaymentNo":  { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.onlinePaymentNo" },
                    "otherPaymentNo":   { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.otherPaymentNo" },
                    "inhousePaymentNo": { "$first": "$analysis_metadata.Data.Summary Of Debit And Credit.inhousePaymentNo" }
                }
            },

            # 6. Calculate inflow/outflow per month
            {
                "$project": {
                    "user_id": "$_id.user_id",
                    "month": "$_id.month",
                    "parsedMonthDate": "$parsedMonthDate",   # ✅ reuse stored value, no recompute
                    "mw_inflow_val": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashdeposit",   "0"] } },
                            { "$toDouble": { "$ifNull": ["$chequeReceipt", "0"] } },
                            { "$toDouble": { "$ifNull": ["$onlineReceipt", "0"] } },
                            { "$toDouble": { "$ifNull": ["$otherRecipt",   "0"] } },
                            { "$toDouble": { "$ifNull": ["$inhouseRecipt", "0"] } }
                        ]
                    },
                    "mw_inflow_no": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashdepositNo",   0] } },
                            { "$toDouble": { "$ifNull": ["$chequeReceiptNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$onlineReceiptNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$otherReciptNo",   0] } },
                            { "$toDouble": { "$ifNull": ["$inhouseReciptNo", 0] } }
                        ]
                    },
                    "mw_outflow_val": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashwithDraw",   "0"] } },
                            { "$toDouble": { "$ifNull": ["$chequePayment",  "0"] } },
                            { "$toDouble": { "$ifNull": ["$onlinePayment",  "0"] } },
                            { "$toDouble": { "$ifNull": ["$otherPayment",   "0"] } },
                            { "$toDouble": { "$ifNull": ["$inhousePayment", "0"] } }
                        ]
                    },
                    "mw_outflow_no": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashwithDrawNo",   0] } },
                            { "$toDouble": { "$ifNull": ["$chequePaymentNo",  0] } },
                            { "$toDouble": { "$ifNull": ["$onlinePaymentNo",  0] } },
                            { "$toDouble": { "$ifNull": ["$otherPaymentNo",   0] } },
                            { "$toDouble": { "$ifNull": ["$inhousePaymentNo", 0] } }
                        ]
                    }
                }
            },

            # 7. Sort ascending by month
            {
                "$sort": {
                    "user_id": 1,
                    "parsedMonthDate": 1
                }
            },

            # 8. Final group by user
            {
                "$group": {
                    "_id": "$user_id",
                    "monthly_breakdown": {
                        "$push": {
                            "month": "$month",
                            "total_Inflows_VALUE":  "$mw_inflow_val",
                            "total_Inflows_NO":     "$mw_inflow_no",
                            "total_Outflows_VALUE": "$mw_outflow_val",
                            "total_Outflows_NO":    "$mw_outflow_no"
                        }
                    },
                    "total_Inflows_VALUE":  { "$sum": "$mw_inflow_val" },
                    "total_Inflows_NO":     { "$sum": "$mw_inflow_no" },
                    "total_Outflows_VALUE": { "$sum": "$mw_outflow_val" },
                    "total_Outflows_NO":    { "$sum": "$mw_outflow_no" }
                }
            }
        ]
            
    
    
    except Exception as e:
        logger.error(
            "bank_statement_report.preflight_failed | user_id=%s | error=%s",
            user_id, str(e), exc_info=True
        )
        raise

    try:
        pipeline_start = time.perf_counter()
        cursor = db.bankstatementreport.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        pipeline_end = time.perf_counter()
        logger.info(
            "bank_statement_report.aggregation_completed | user_id=%s | pipeline_time=%.2f seconds | result_count=%s",
            user_id, pipeline_end - pipeline_start, len(result)
        )
        if not result:
            logger.warning("bank_Statement_Report aggregation | user_id=%s | Message:no data found after aggregation ",user_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message":"No summary data found for this user in the given date range"})
        
        # --- Format response to match frontend structure ---
        raw = result[0]

        formatted_breakdown = []
        for entry in raw.get("monthly_breakdown", []):
            formatted_breakdown.append({
                "month": entry["month"].lower(),
                "inflows_value": {
                    "total_receipt_inflows_value": entry["total_Inflows_VALUE"]
                },
                "inflows_no": {
                    "total_receipt_inflows_no": entry["total_Inflows_NO"]
                },
                "outflows_value": {
                    "total_payments_outflows_value": entry["total_Outflows_VALUE"]
                },
                "outflows_no": {
                    "total_payments_outflows_no": entry["total_Outflows_NO"]
                }
            })

        formatted_response = {
            "_id": raw["_id"],
            "monthly_breakdown": formatted_breakdown,
            "total": {
                "total_receipt_inflows_value":   raw["total_Inflows_VALUE"],
                "total_receipt_inflows_no":      raw["total_Inflows_NO"],
                "total_payments_outflows_value": raw["total_Outflows_VALUE"],
                "total_payments_outflows_no":    raw["total_Outflows_NO"]
            }
        }

        total_time = time.perf_counter() - start_time
        logger.info("total_time | user_id=%s | %.2fs", user_id, total_time)
        return formatted_response
    except HTTPException:
        raise   
    except Exception as e:
        logger.error(
            "bank_statement_report.aggregation_failed | user_id=%s | error=%s",
            user_id, str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={"message": "Unexpected error during aggregation"}
        )


            
        



