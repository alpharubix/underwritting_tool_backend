# verify_pipeline.py
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
# from controller.bank_statement_report import bank_statement_report


MONGO_URI = "mongodb+srv://techalpharubixinfotech:k977aHiL1bRkdDJa@cluster0.okx9fa7.mongodb.net"
DB_NAME   = "underwriting"
USER_ID   = "69dcbe4e0b3946becc82562a"  # from the sample doc you shared


# ── Paste your pipeline function directly here ─────────────────────────────
async def bank_statement_report(db, user_id: str):
    exists = await db.bankstatementreport.find_one({"user_id": user_id}, {"_id": 1})
    if not exists:
        return None

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$unwind": "$bank_statments"},
        {
            "$group": {
                "_id": "$user_id",
                "reference_ids": {"$addToSet": "$reference_id"},
                "report_count":  {"$addToSet": "$reference_id"},
                "sum_credit":   {"$sum": "$bank_statments.Credit"},
                "cnt_credit":   {"$sum": {"$cond": [{"$gt": ["$bank_statments.Credit", 0]}, 1, 0]}},
                "sum_debit":    {"$sum": "$bank_statments.Debit"},
                "cnt_debit":    {"$sum": {"$cond": [{"$gt": ["$bank_statments.Debit", 0]}, 1, 0]}},
                "val_outward_chq_ret": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]}, "$bank_statments.Credit", 0]}
                },
                "val_inward_chq_ret_credit": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]}, "$bank_statments.Credit", 0]}
                },
                "val_inward_online_ret": {
                    "$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Inward Online Return", "Online Return"]]}, "$bank_statments.Credit", 0]}
                },
                "val_inward_chq_ret_debit": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]}, "$bank_statments.Debit", 0]}
                },
                "val_outward_chq_ret_debit": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]}, "$bank_statments.Debit", 0]}
                },
                "val_outward_online_ret": {
                    "$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Outward Online Return", "Online Return"]]}, "$bank_statments.Debit", 0]}
                },
                "val_contra": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Contra"]}, "$bank_statments.Debit", 0]}
                },
                "val_inhouse_debit": {
                    "$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Inhouse Debit"]}, "$bank_statments.Debit", 0]}
                },
                "nos_inward_chq_ret":     {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]},  1, 0]}},
                "nos_total_chq_received": {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Cheque Receipt"]},         1, 0]}},
                "nos_outward_chq_ret":    {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]},  1, 0]}},
                "nos_total_chq_paid":     {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Cheque Payment"]},         1, 0]}},
                "nos_inward_online_ret":  {"$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Inward Online Return", "Online Return"]]}, 1, 0]}},
                "nos_total_online_credits":{"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Online Receipt"]},        1, 0]}},
                "nos_outward_online_ret": {"$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Outward Online Return", "Online Return"]]}, 1, 0]}},
                "nos_total_online_debits":{"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Online Payment"]},         1, 0]}},
                "nos_ecs_return":         {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "ECS/NACH Return"]},        1, 0]}},
                "nos_total_ecs_payments": {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "ECS/NACH Payment"]},       1, 0]}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "user_id":      "$_id",
                "reference_ids": 1,
                "report_count": {"$size": "$report_count"},
                "overview": {
                    "average_credit_tranx": {"$cond": [{"$eq": ["$cnt_credit", 0]}, 0, {"$round": [{"$divide": ["$sum_credit", "$cnt_credit"]}, 2]}]},
                    "total_credit_nos": "$cnt_credit",
                    "average_debit_tranx": {"$cond": [{"$eq": ["$cnt_debit", 0]}, 0, {"$round": [{"$divide": ["$sum_debit", "$cnt_debit"]}, 2]}]},
                    "total_debit_nos": "$cnt_debit",
                },
                "cash_inflow": {
                    "total_credits_A":                "$sum_credit",
                    "outward_cheque_return_B":         "$val_outward_chq_ret",
                    "reversal_inward_cheque_return_C": "$val_inward_chq_ret_credit",
                    "reversal_online_return_D":        "$val_inward_online_ret",
                    "gross_credits_E": {
                        "$subtract": ["$sum_credit", {"$add": ["$val_outward_chq_ret", "$val_inward_chq_ret_credit", "$val_inward_online_ret"]}]
                    },
                },
                "cash_outflow": {
                    "total_debits_A":                    "$sum_debit",
                    "inward_cheque_return_B":             "$val_inward_chq_ret_debit",
                    "reversal_outward_cheque_return_C":   "$val_outward_chq_ret_debit",
                    "online_return_D":                    "$val_outward_online_ret",
                    "gross_debits_E": {
                        "$subtract": ["$sum_debit", {"$add": ["$val_inward_chq_ret_debit", "$val_outward_chq_ret_debit", "$val_outward_online_ret"]}]
                    },
                    "contra_F":       "$val_contra",
                    "net_debits_G": {
                        "$subtract": [
                            {"$subtract": ["$sum_debit", {"$add": ["$val_inward_chq_ret_debit", "$val_outward_chq_ret_debit", "$val_outward_online_ret"]}]},
                            "$val_contra"
                        ]
                    },
                    "inhouse_debit_H": "$val_inhouse_debit",
                    "net_cash_outflow": {
                        "$subtract": [
                            {"$subtract": [
                                {"$subtract": ["$sum_debit", {"$add": ["$val_inward_chq_ret_debit", "$val_outward_chq_ret_debit", "$val_outward_online_ret"]}]},
                                "$val_contra"
                            ]},
                            "$val_inhouse_debit"
                        ]
                    },
                },
                "returns": {
                    "inward_cheque_return_nos": "$nos_inward_chq_ret",
                    "inward_cheque_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_chq_received", 0]}, 0,
                            {"$round": [{"$multiply": [{"$divide": ["$nos_inward_chq_ret", "$nos_total_chq_received"]}, 100]}, 2]}]
                    },
                    "outward_cheque_return_nos": "$nos_outward_chq_ret",
                    "outward_cheque_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_chq_paid", 0]}, 0,
                            {"$round": [{"$multiply": [{"$divide": ["$nos_outward_chq_ret", "$nos_total_chq_paid"]}, 100]}, 2]}]
                    },
                    "inward_online_return_nos": "$nos_inward_online_ret",
                    "inward_online_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_online_credits", 0]}, 0,
                            {"$round": [{"$multiply": [{"$divide": ["$nos_inward_online_ret", "$nos_total_online_credits"]}, 100]}, 2]}]
                    },
                    "outward_online_return_nos": "$nos_outward_online_ret",
                    "outward_online_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_online_debits", 0]}, 0,
                            {"$round": [{"$multiply": [{"$divide": ["$nos_outward_online_ret", "$nos_total_online_debits"]}, 100]}, 2]}]
                    },
                    "ecs_return_nos": "$nos_ecs_return",
                    "ecs_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_ecs_payments", 0]}, 0,
                            {"$round": [{"$multiply": [{"$divide": ["$nos_ecs_return", "$nos_total_ecs_payments"]}, 100]}, 2]}]
                    },
                }
            }
        }
    ]

    cursor = db.bankstatementreport.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    return result[0] if result else None


async def run():
    client = AsyncIOMotorClient(MONGO_URI)
    db     = client[DB_NAME]

    docs  = await db.bankstatementreport.find({"user_id": USER_ID}).to_list(length=None)
    if not docs:
        print("❌ Document not found - check USER_ID and DB_NAME")
        return

    stmts = []
    for doc in docs:
        stmts.extend(doc["bank_statments"])

    print(f"Found {len(docs)} document(s) for this user")
    print(f"Total transactions: {len(stmts)}")
    
    # stmts = doc["bank_statments"]

    # ── Expected from raw transactions ────────────────────────────────────────
    expected = {
        "sum_credit":              sum(s["Credit"] for s in stmts),
        "cnt_credit":              sum(1 for s in stmts if s["Credit"] > 0),
        "sum_debit":               sum(s["Debit"]  for s in stmts),
        "cnt_debit":               sum(1 for s in stmts if s["Debit"]  > 0),
        "outward_chq_ret_credit":  sum(s["Credit"] for s in stmts if s["FirstLevelClassification"] == "Outward Cheque Return"),
        "inward_chq_ret_credit":   sum(s["Credit"] for s in stmts if s["FirstLevelClassification"] == "Inward Cheque Return"),
        "inward_online_ret":       sum(s["Credit"] for s in stmts if s["FirstLevelClassification"] in ["Inward Online Return", "Online Return"]),
        "inward_chq_ret_debit":    sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] == "Inward Cheque Return"),
        "outward_chq_ret_debit":   sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] == "Outward Cheque Return"),
        "outward_online_ret":      sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] in ["Outward Online Return", "Online Return"]),
        "contra_debit":            sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] == "Contra"),
        "inhouse_debit":           sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] == "Inhouse Debit"),
        "nos_inward_chq_ret":      sum(1 for s in stmts if s["FirstLevelClassification"] == "Inward Cheque Return"),
        "nos_chq_received":        sum(1 for s in stmts if s["FirstLevelClassification"] == "Cheque Receipt"),
        "nos_outward_chq_ret":     sum(1 for s in stmts if s["FirstLevelClassification"] == "Outward Cheque Return"),
        "nos_chq_paid":            sum(1 for s in stmts if s["FirstLevelClassification"] == "Cheque Payment"),
        "nos_ecs_return":          sum(1 for s in stmts if s["FirstLevelClassification"] == "ECS/NACH Return"),
        "nos_ecs_payment":         sum(1 for s in stmts if s["FirstLevelClassification"] == "ECS/NACH Payment"),
    }

    # Derived
    gc_E  = expected["sum_credit"] - expected["outward_chq_ret_credit"] - expected["inward_chq_ret_credit"] - expected["inward_online_ret"]
    gd_E  = expected["sum_debit"]  - expected["inward_chq_ret_debit"]   - expected["outward_chq_ret_debit"]  - expected["outward_online_ret"]
    nd_G  = gd_E  - expected["contra_debit"]
    nco   = nd_G  - expected["inhouse_debit"]
    avg_c = round(expected["sum_credit"] / expected["cnt_credit"], 2) if expected["cnt_credit"] else 0
    avg_d = round(expected["sum_debit"]  / expected["cnt_debit"],  2) if expected["cnt_debit"]  else 0

    # ── Run pipeline ──────────────────────────────────────────────────────────
    result = await bank_statement_report(db, USER_ID)
    if not result:
        print("❌ Pipeline returned nothing")
        return

    ov = result["overview"]
    ci = result["cash_inflow"]
    co = result["cash_outflow"]
    rt = result["returns"]

    # ── Assert ────────────────────────────────────────────────────────────────
    checks = [
        ("overview.total_credit_nos",    ov["total_credit_nos"],     expected["cnt_credit"]),
        ("overview.average_credit_tranx",ov["average_credit_tranx"], avg_c),
        ("overview.total_debit_nos",     ov["total_debit_nos"],      expected["cnt_debit"]),
        ("overview.average_debit_tranx", ov["average_debit_tranx"],  avg_d),
        ("cash_inflow.total_credits_A",  ci["total_credits_A"],      expected["sum_credit"]),
        ("cash_inflow.gross_credits_E",  ci["gross_credits_E"],      gc_E),
        ("cash_outflow.total_debits_A",  co["total_debits_A"],       expected["sum_debit"]),
        ("cash_outflow.gross_debits_E",  co["gross_debits_E"],       gd_E),
        ("cash_outflow.contra_F",        co["contra_F"],             expected["contra_debit"]),
        ("cash_outflow.net_debits_G",    co["net_debits_G"],         nd_G),
        ("cash_outflow.inhouse_debit_H", co["inhouse_debit_H"],      expected["inhouse_debit"]),
        ("cash_outflow.net_cash_outflow",co["net_cash_outflow"],     nco),
        ("returns.ecs_return_nos",       rt["ecs_return_nos"],       expected["nos_ecs_return"]),
    ]

    print(f"\n── Checking user: {USER_ID} ──────────────────────────────────────────────")
    all_passed = True
    for name, got, want in checks:
        passed = round(float(got), 2) == round(float(want), 2)
        status = "✅" if passed else "❌"
        if not passed:
            all_passed = False
        print(f"  {status}  {name:<40} got={got}  expected={want}")

    # ── Classification breakdown ──────────────────────────────────────────────
    print(f"\n── All classifications in this document ──────────────────────────────────")
    classifications = sorted(set(s["FirstLevelClassification"] for s in stmts))
    for c in classifications:
        cr = sum(s["Credit"] for s in stmts if s["FirstLevelClassification"] == c)
        dr = sum(s["Debit"]  for s in stmts if s["FirstLevelClassification"] == c)
        n  = sum(1           for s in stmts if s["FirstLevelClassification"] == c)
        print(f"  {c:<30}  n={n:<5}  credit={cr:<14.2f}  debit={dr:.2f}")

    print(f"\n{'✅  ALL CHECKS PASSED' if all_passed else '❌  SOME CHECKS FAILED'}\n")
    client.close()


asyncio.run(run())