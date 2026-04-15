import logging
import time
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def bank_statement_report(db,user_id:str):

    logger.info("bank_statement_report.start | user_id=%s", user_id)
    start_time = time.perf_counter()

    try:
        exists = await db.bankstatementreport.find_one({"user_id": user_id}, {"_id": 1})
    except Exception as e:
        logger.error(
            "bank_statement_report.preflight_failed | user_id=%s | error=%s",
            user_id, str(e), exc_info=True
        )
        raise
    if not exists:
        logger.warning(
            "bank_statement_report.not_found | user_id=%s | message=no documents found",
            user_id
        )
        return None
    try:
        doc_count = await db.bankstatementreport.count_documents({"user_id": user_id})
        logger.info(
            "bank_statement_report.documents_found | user_id=%s | doc_count=%d",
            user_id, doc_count
        )
    except Exception as e:
        logger.warning(
            "bank_statement_report.count_failed | user_id=%s | error=%s",
            user_id, str(e)
        )

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$unwind": "$bank_statments"},
        {
            "$group": {
                "_id": "$user_id",

                "reference_ids": {"$addToSet": "$reference_id"},
                "report_count":  {"$addToSet": "$reference_id"},

                # ── OVERVIEW ──────────────────────────────────────────────
                "sum_credit": {"$sum": "$bank_statments.Credit"},
                "cnt_credit": {"$sum": {"$cond": [{"$gt": ["$bank_statments.Credit", 0]}, 1, 0]}},
                "sum_debit":  {"$sum": "$bank_statments.Debit"},
                "cnt_debit":  {"$sum": {"$cond": [{"$gt": ["$bank_statments.Debit", 0]}, 1, 0]}},

                # ── CASH INFLOW ────────────────────────────────────────────
                # B — Outward Cheque Return credit side
                "val_outward_chq_ret_cr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]},
                        "$bank_statments.Credit", 0
                    ]}
                },
                # C — Inward Cheque Return credit side
                "val_inward_chq_ret_cr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]},
                        "$bank_statments.Credit", 0
                    ]}
                },
                # D — Inward Online Return credit side
                "val_inward_online_ret_cr": {
                    "$sum": {"$cond": [
                        {"$in": ["$bank_statments.FirstLevelClassification",
                                 ["Inward Online Return", "Online Return"]]},
                        "$bank_statments.Credit", 0
                    ]}
                },

                # ── CASH OUTFLOW ───────────────────────────────────────────
                # B — Inward Cheque Return debit side
                "val_inward_chq_ret_dr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]},
                        "$bank_statments.Debit", 0
                    ]}
                },
                # C — Outward Cheque Return debit side
                "val_outward_chq_ret_dr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]},
                        "$bank_statments.Debit", 0
                    ]}
                },
                # D — Outward Online Return debit side
                "val_outward_online_ret_dr": {
                    "$sum": {"$cond": [
                        {"$in": ["$bank_statments.FirstLevelClassification",
                                 ["Outward Online Return", "Online Return"]]},
                        "$bank_statments.Debit", 0
                    ]}
                },
                # F — Contra debit only
                "val_contra_dr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Contra"]},
                        "$bank_statments.Debit", 0
                    ]}
                },
                # H — Inhouse Debit
                "val_inhouse_dr": {
                    "$sum": {"$cond": [
                        {"$eq": ["$bank_statments.FirstLevelClassification", "Inhouse Debit"]},
                        "$bank_statments.Debit", 0
                    ]}
                },

                # ── RETURNS — counts ───────────────────────────────────────
                "nos_inward_chq_ret":      {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Inward Cheque Return"]},  1, 0]}},
                "nos_total_chq_received":  {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Cheque Receipt"]},         1, 0]}},
                "nos_outward_chq_ret":     {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Outward Cheque Return"]},  1, 0]}},
                "nos_total_chq_paid":      {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Cheque Payment"]},         1, 0]}},
                "nos_inward_online_ret":   {"$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Inward Online Return",  "Online Return"]]}, 1, 0]}},
                "nos_total_online_cr":     {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Online Receipt"]},         1, 0]}},
                "nos_outward_online_ret":  {"$sum": {"$cond": [{"$in": ["$bank_statments.FirstLevelClassification", ["Outward Online Return", "Online Return"]]}, 1, 0]}},
                "nos_total_online_dr":     {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "Online Payment"]},         1, 0]}},
                "nos_ecs_return":          {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "ECS/NACH Return"]},        1, 0]}},
                "nos_total_ecs_payment":   {"$sum": {"$cond": [{"$eq": ["$bank_statments.FirstLevelClassification", "ECS/NACH Payment"]},       1, 0]}},
            }
        },

        # STAGE 4 — apply every formula, produce final response shape
        {
            "$project": {
                "_id":           0,
                "user_id":       "$_id",
                "report_count":  {"$size": "$report_count"},
                "reference_ids": 1,

                # ── OVERVIEW ──────────────────────────────────────────────
                "overview": {
                    "average_credit_tranx": {
                        "$cond": [{"$eq": ["$cnt_credit", 0]}, 0,
                                  {"$round": [{"$divide": ["$sum_credit", "$cnt_credit"]}, 2]}]
                    },
                    "total_credit_nos": "$cnt_credit",
                    "average_debit_tranx": {
                        "$cond": [{"$eq": ["$cnt_debit", 0]}, 0,
                                  {"$round": [{"$divide": ["$sum_debit", "$cnt_debit"]}, 2]}]
                    },
                    "total_debit_nos": "$cnt_debit",
                },

                # ── CASH INFLOW ────────────────────────────────────────────
                # A - B - C - D = E
                "cash_inflow": {
                    "total_credits_A":                "$sum_credit",
                    "outward_cheque_return_B":         "$val_outward_chq_ret_cr",
                    "reversal_inward_cheque_return_C": "$val_inward_chq_ret_cr",
                    "reversal_online_return_D":        "$val_inward_online_ret_cr",
                    "gross_credits_E": {
                        "$subtract": [
                            "$sum_credit",
                            {"$add": [
                                "$val_outward_chq_ret_cr",
                                "$val_inward_chq_ret_cr",
                                "$val_inward_online_ret_cr"
                            ]}
                        ]
                    },
                },

                # ── CASH OUTFLOW ───────────────────────────────────────────
                # A - B - C - D = E,  E - F = G,  G - H = Net
                "cash_outflow": {
                    "total_debits_A":                   "$sum_debit",
                    "inward_cheque_return_B":            "$val_inward_chq_ret_dr",
                    "reversal_outward_cheque_return_C":  "$val_outward_chq_ret_dr",
                    "online_return_D":                   "$val_outward_online_ret_dr",
                    "gross_debits_E": {
                        "$subtract": [
                            "$sum_debit",
                            {"$add": [
                                "$val_inward_chq_ret_dr",
                                "$val_outward_chq_ret_dr",
                                "$val_outward_online_ret_dr"
                            ]}
                        ]
                    },
                    "contra_F":        "$val_contra_dr",
                    "net_debits_G": {
                        "$subtract": [
                            {"$subtract": [
                                "$sum_debit",
                                {"$add": [
                                    "$val_inward_chq_ret_dr",
                                    "$val_outward_chq_ret_dr",
                                    "$val_outward_online_ret_dr"
                                ]}
                            ]},
                            "$val_contra_dr"
                        ]
                    },
                    "inhouse_debit_H": "$val_inhouse_dr",
                    "net_cash_outflow": {
                        "$subtract": [
                            {"$subtract": [
                                {"$subtract": [
                                    "$sum_debit",
                                    {"$add": [
                                        "$val_inward_chq_ret_dr",
                                        "$val_outward_chq_ret_dr",
                                        "$val_outward_online_ret_dr"
                                    ]}
                                ]},
                                "$val_contra_dr"
                            ]},
                            "$val_inhouse_dr"
                        ]
                    },
                },

                # ── RETURNS ────────────────────────────────────────────────
                "returns": {
                    "inward_cheque_return_nos": "$nos_inward_chq_ret",
                    "inward_cheque_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_chq_received", 0]}, 0,
                                  {"$round": [{"$multiply": [{"$divide": ["$nos_inward_chq_ret",
                                                                           "$nos_total_chq_received"]}, 100]}, 2]}]
                    },
                    "outward_cheque_return_nos": "$nos_outward_chq_ret",
                    "outward_cheque_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_chq_paid", 0]}, 0,
                                  {"$round": [{"$multiply": [{"$divide": ["$nos_outward_chq_ret",
                                                                           "$nos_total_chq_paid"]}, 100]}, 2]}]
                    },
                    "inward_online_return_nos": "$nos_inward_online_ret",
                    "inward_online_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_online_cr", 0]}, 0,
                                  {"$round": [{"$multiply": [{"$divide": ["$nos_inward_online_ret",
                                                                           "$nos_total_online_cr"]}, 100]}, 2]}]
                    },
                    "outward_online_return_nos": "$nos_outward_online_ret",
                    "outward_online_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_online_dr", 0]}, 0,
                                  {"$round": [{"$multiply": [{"$divide": ["$nos_outward_online_ret",
                                                                           "$nos_total_online_dr"]}, 100]}, 2]}]
                    },
                    "ecs_return_nos": "$nos_ecs_return",
                    "ecs_return_percent": {
                        "$cond": [{"$eq": ["$nos_total_ecs_payment", 0]}, 0,
                                  {"$round": [{"$multiply": [{"$divide": ["$nos_ecs_return",
                                                                           "$nos_total_ecs_payment"]}, 100]}, 2]}]
                    },
                }
            }
        }
    ]
    

    
    # try:    
    #     cursor=db.bankstatementreport.aggregate(pipeline)
    #     result= await cursor.to_list(length=1)
    #     return result[0] if result else None
    # except Exception as e:
    #     raise
    

    try:
        logger.debug(
            "bank_statement_report.pipeline_start | user_id=%s | stages=%d",
            user_id, len(pipeline)
        )
        pipeline_start = time.perf_counter()

        cursor = db.bankstatementreport.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        pipeline_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "bank_statement_report.pipeline_done | user_id=%s | duration_ms=%.2f",
            user_id, pipeline_ms
        )

        if not result:
            logger.warning(
                "bank_statement_report.empty_result | user_id=%s",
                user_id
            )
            return None

        logger.info(
            "bank_statement_report.success | user_id=%s | duration_ms=%.2f",
            user_id, pipeline_ms
        )
        return result[0]

    except Exception as e:
        elapsed_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.error(
            "bank_statement_report.pipeline_failed | user_id=%s | duration_ms=%.2f | error=%s",
            user_id, elapsed_ms, str(e), exc_info=True
        )
        raise