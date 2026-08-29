from asyncio.log import logger
from datetime import datetime
from http.client import HTTPException
from http.client import HTTPException
from time import time

from underwritting_tool_backend.controller.cashflow_controller import normalize_date_range


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

    try:
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
                    "analysis_metadata.Data.Summary Of Debit And Credit": 1
                }
            },

            # 3. Unwind
            {
                "$unwind": "$analysis_metadata.Data.Summary Of Debit And Credit"
            },

            # 4. Filter by date range using stored parsedMonthDate
            {
                "$match": {
                    "analysis_metadata.Data.Summary Of Debit And Credit.parsedMonthDate": {
                        "$gte": normalized_from,
                        "$lte": normalized_to
                    }
                }
            },

            # 5. Calculate inflow/outflow per month (no dedup needed — single doc per user)
            {
                "$project": {
                    "user_id": 1,
                    "month": "$analysis_metadata.Data.Summary Of Debit And Credit.month",
                    "parsedMonthDate": "$analysis_metadata.Data.Summary Of Debit And Credit.parsedMonthDate",
                    "mw_inflow_val": {
                        "$add": [
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashdeposit", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceipt", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceipt", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherRecipt", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhouseRecipt", "0"]}}
                        ]
                    },
                    "mw_inflow_val_breakdown": {
                            "cash_deposit":    {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashdeposit", "0"]}},
                            "cheque_receipt":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceipt", "0"]}},
                            "online_receipt":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceipt", "0"]}},
                            "other_receipt":   {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherRecipt", "0"]}},
                            "inhouse_receipt": {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhouseRecipt", "0"]}},
                    },
                    "mw_inflow_no": {
                        "$add": [
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashdepositNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceiptNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceiptNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherReciptNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhouseReciptNo", 0]}}
                        ]
                    },
                    "mw_inflow_no_breakdown": {
                            "cash_deposit_no":    {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashdepositNo", "0"]}},
                            "cheque_receipt_no":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequeReceiptNo", "0"]}},
                            "online_receipt_no":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlineReceiptNo", "0"]}},
                            "other_receipt_no":   {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherReciptNo", "0"]}},
                            "inhouse_receipt_no": {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhouseReciptNo", "0"]}},
                    },
                    "mw_outflow_val": {
                        "$add": [
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDraw", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequePayment", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlinePayment", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherPayment", "0"]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhousePayment", "0"]}}
                        ]
                    },
                    "mw_outflow_val_breakdown": {
                            "cash_withdrawal":    {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDraw", "0"]}},
                            "cheque_payment":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequePayment", "0"]}},
                            "online_payment":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlinePayment", "0"]}},
                            "other_payment":   {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherPayment", "0"]}},
                            "inhouse_payment": {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhousePayment", "0"]}},
                    },
                    "mw_outflow_no": {
                        "$add": [
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDrawNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequePaymentNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlinePaymentNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherPaymentNo", 0]}},
                            {"$toDouble": {
                                "$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhousePaymentNo", 0]}}
                        ]
                    },
                    "mw_outflow_no_breakdown": {
                            "cash_withdrawal_no":    {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.cashwithDrawNo", "0"]}},
                            "cheque_payment_no":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.chequePaymentNo", "0"]}},
                            "online_payment_no":  {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.onlinePaymentNo", "0"]}},
                            "other_payment_no":   {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.otherPaymentNo", "0"]}},
                            "inhouse_payment_no": {"$toDouble": {"$ifNull": ["$analysis_metadata.Data.Summary Of Debit And Credit.inhousePaymentNo", "0"]}},
                    },
                }
            },

            # 6. Sort ascending by month
            {
                "$sort": {
                    "parsedMonthDate": 1
                }
            },

            # 7. Final group by user — build monthly breakdown + totals
            {
                "$group": {
                    "_id": "$user_id",
                    "monthly_breakdown": {
                        "$push": {
                            "month": "$month",
                            "total_Inflows_VALUE": "$mw_inflow_val",
                            "total_Inflows_NO": "$mw_inflow_no",
                            "total_Outflows_VALUE": "$mw_outflow_val",
                            "total_Outflows_NO": "$mw_outflow_no",
                            "inflows_value_breakdown": "$mw_inflow_val_breakdown",
                            "inflows_no_breakdown": "$mw_inflow_no_breakdown",
                            "outflows_value_breakdown": "$mw_outflow_val_breakdown",
                            "outflows_no_breakdown": "$mw_outflow_no_breakdown",
                        }
                    },
                    "total_Inflows_VALUE": {"$sum": "$mw_inflow_val"},
                    "total_Inflows_NO": {"$sum": "$mw_inflow_no"},
                    "total_Outflows_VALUE": {"$sum": "$mw_outflow_val"},
                    "total_Outflows_NO": {"$sum": "$mw_outflow_no"},
                    "total_cash_deposit_val":    {"$sum": "$mw_inflow_val_breakdown.cash_deposit"},
                    "total_cheque_receipt_val":  {"$sum": "$mw_inflow_val_breakdown.cheque_receipt"},
                    "total_online_receipt_val":  {"$sum": "$mw_inflow_val_breakdown.online_receipt"},
                    "total_other_receipt_val":   {"$sum": "$mw_inflow_val_breakdown.other_receipt"},
                    "total_inhouse_receipt_val": {"$sum": "$mw_inflow_val_breakdown.inhouse_receipt"},

                    "total_cash_deposit_no":    {"$sum": "$mw_inflow_no_breakdown.cash_deposit_no"},
                    "total_cheque_receipt_no":  {"$sum": "$mw_inflow_no_breakdown.cheque_receipt_no"},
                    "total_online_receipt_no":  {"$sum": "$mw_inflow_no_breakdown.online_receipt_no"},
                    "total_other_receipt_no":   {"$sum": "$mw_inflow_no_breakdown.other_receipt_no"},
                    "total_inhouse_receipt_no": {"$sum": "$mw_inflow_no_breakdown.inhouse_receipt_no"},

                    "total_cash_withdraw_val":   {"$sum": "$mw_outflow_val_breakdown.cash_withdraw"},
                    "total_cheque_payment_val":  {"$sum": "$mw_outflow_val_breakdown.cheque_payment"},
                    "total_online_payment_val":  {"$sum": "$mw_outflow_val_breakdown.online_payment"},
                    "total_other_payment_val":   {"$sum": "$mw_outflow_val_breakdown.other_payment"},
                    "total_inhouse_payment_val": {"$sum": "$mw_outflow_val_breakdown.inhouse_payment"},

                    "total_cash_withdraw_no":   {"$sum": "$mw_outflow_no_breakdown.cash_withdrawal_no"},
                    "total_cheque_payment_no":  {"$sum": "$mw_outflow_no_breakdown.cheque_payment_no"},
                    "total_online_payment_no":  {"$sum": "$mw_outflow_no_breakdown.online_payment_no"},
                    "total_other_payment_no":   {"$sum": "$mw_outflow_no_breakdown.other_payment_no"},
                    "total_inhouse_payment_no": {"$sum": "$mw_outflow_no_breakdown.inhouse_payment_no"},
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
        cursor = db.bsa_merged_bankstatements.aggregate(pipeline)
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
                    "inflows_value_breakdown": entry.get("inflows_value_breakdown", {}),
                    "total_receipt_inflows_value": entry["total_Inflows_VALUE"]
                },
                "inflows_no": {
                    "inflows_no_breakdown": entry.get("inflows_no_breakdown", {}),
                    "total_receipt_inflows_no": entry["total_Inflows_NO"]
                },
                "outflows_value": {
                    "outflows_value_breakdown": entry.get("outflows_value_breakdown", {}),
                    "total_payments_outflows_value": entry["total_Outflows_VALUE"]
                },
                "outflows_no": {
                    "outflows_no_breakdown": entry.get("outflows_no_breakdown", {}),
                    "total_payments_outflows_no": entry["total_Outflows_NO"]
                },
            })

        formatted_response = {
            "_id": raw["_id"],
            "monthly_breakdown": formatted_breakdown,
            "total": {
                "total_receipt_inflows_value":   raw["total_Inflows_VALUE"],
                "total_receipt_inflows_no":      raw["total_Inflows_NO"],
                "total_payments_outflows_value": raw["total_Outflows_VALUE"],
                "total_payments_outflows_no":    raw["total_Outflows_NO"],

                # Phase 2 — breakdown totals

                "inflows_value_breakdown": {
                    "cash_deposit":    raw["total_cash_deposit_val"],
                    "cheque_receipt":  raw["total_cheque_receipt_val"],
                    "online_receipt":  raw["total_online_receipt_val"],
                    "other_receipt":   raw["total_other_receipt_val"],
                    "inhouse_receipt": raw["total_inhouse_receipt_val"],
                },
                "inflows_no_breakdown": {
                    "cash_deposit":    raw["total_cash_deposit_no"],
                    "cheque_receipt":  raw["total_cheque_receipt_no"],
                    "online_receipt":  raw["total_online_receipt_no"],
                    "other_receipt":   raw["total_other_receipt_no"],
                    "inhouse_receipt": raw["total_inhouse_receipt_no"],
                },
                "outflows_value_breakdown": {
                    "cash_withdrawal":   raw["total_cash_withdraw_val"],
                    "cheque_payment":  raw["total_cheque_payment_val"],
                    "online_payment":  raw["total_online_payment_val"],
                    "other_payment":   raw["total_other_payment_val"],
                    "inhouse_payment": raw["total_inhouse_payment_val"],
                },
                "outflows_no_breakdown": {
                    "cash_withdrawal_no":   raw["total_cash_withdraw_no"],
                    "cheque_payment_no":  raw["total_cheque_payment_no"],
                    "online_payment_no":  raw["total_online_payment_no"],
                    "other_payment_no":   raw["total_other_payment_no"],
                    "inhouse_payment_no": raw["total_inhouse_payment_no"],
                },

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


            
        



#optimization:
# 1. Early projection to drop heavy fields before unwind.
# Step 2 (Optimized)
async def optimize_bsa_summary_of_debit_credit_monthwise(db,user_id:str,from_date,to_date):
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

    try:
        pipeline = [
            {
                "$project": {
                    "user_id": 1,
                    "summary": {
                        "$filter": {
                            "input": "$analysis_metadata.Data.Summary Of Debit And Credit",
                            "as": "month",
                            "cond": {
                                "$and": [
                                    {
                                        "$gte": [
                                            "$$month.parsedMonthDate",
                                            normalized_from
                                        ]
                                    },
                                    {
                                        "$lte": [
                                            "$$month.parsedMonthDate",
                                            normalized_to
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {
                "$unwind": "$summary"
            }
        ]

        total_time = time.perf_counter() - start_time
        logger.info("total_time | user_id=%s | %.2fs", user_id, total_time)
        return pipeline
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "optimize_bsa_summary_of_debit_credit_monthwise.failed | user_id=%s | error=%s",
            user_id, str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={"message": "Unexpected error during optimization"}
        )