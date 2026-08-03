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


async def bsa_summary_of_debit_credit_monthwise_oldVersion(db,user_id:str,from_date,to_date):
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


            
"""
UPDATED VERSION (Review Copy)

NOTE:
This file contains the original implementation with review comments
describing the recommended optimizations.

Recommended improvements applied conceptually:
1. Introduce a temporary alias (`summary`) after `$unwind` using `$set`
   to avoid repeatedly referencing:
   analysis_metadata.Data.Summary Of Debit And Credit

2. Compute numeric conversions once and reuse them instead of repeatedly
   calling `$toDouble + $ifNull`.

3. Reuse breakdown objects instead of rebuilding them multiple times.

4. Push more response shaping into the aggregation pipeline to reduce
   Python-side formatting.

5. Use consistent numeric defaults (`0` instead of `"0"`).

6. Keep naming consistent (cash_withdrawal vs cash_withdraw).

The business logic remains unchanged.
----------------------------------------------------------------------
"""

async def bsa_summary_of_debit_credit_monthwise_prathamesh_first_version(db,user_id:str,from_date,to_date):
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
            # IMPROVEMENT:
            # Only required fields are projected before $unwind.
            # This reduces document size travelling through the pipeline,
            # lowering memory usage and improving aggregation performance.
            {
                "$project": {
                    "user_id": 1,
                    "analysis_metadata.Data.Summary Of Debit And Credit": 1
                }
            },

            # 3. Unwind
            # IMPROVEMENT:
            # Recommended:
            # Immediately follow this stage with:
            #
            # {
            #     "$set": {
            #         "summary": "$analysis_metadata.Data.Summary Of Debit And Credit"
            #     }
            # }
            #
            # This removes hundreds of repeated long field paths later.
            {
                "$unwind": "$analysis_metadata.Data.Summary Of Debit And Credit"
            },

            # 4. Filter by date range using stored parsedMonthDate
            # IMPROVEMENT:
            # Filtering immediately after $unwind minimizes the number
            # of documents processed by expensive projection stages.
            {
                "$match": {
                    "analysis_metadata.Data.Summary Of Debit And Credit.parsedMonthDate": {
                        "$gte": normalized_from,
                        "$lte": normalized_to
                    }
                }
            },

            # 5. Calculate inflow/outflow per month (no dedup needed — single doc per user)
            # IMPROVEMENT:
            # This section contains repeated $toDouble + $ifNull conversions.
            # A cleaner approach is to compute each numeric field once
            # (cash_deposit, cheque_receipt, etc.) and reuse them for:
            #   • totals
            #   • breakdowns
            #   • monthly aggregates
            #
            # This avoids duplicated logic and makes maintenance easier.
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
            # IMPROVEMENT:
            # Sorting after filtering minimizes the number of documents
            # that MongoDB needs to order.
            {
                "$sort": {
                    "parsedMonthDate": 1
                }
            },

            # 7. Final group by user — build monthly breakdown + totals
            # IMPROVEMENT:
            # The current implementation manually sums every field.
            # Consider grouping reusable objects instead of maintaining
            # dozens of individual accumulator fields.
            #
            # This significantly improves maintainability.
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
        # IMPROVEMENT:
        # Most of this formatting can be moved into a final $project stage
        # inside MongoDB, allowing Python to simply return result[0].
        # This reduces application-side processing.
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
            ############################################################
            #
            # EXISTING PROBLEM
            #
            # The previous approach carried the full monthly summary array farther
            # through the pipeline before reducing it to the requested date range.
            # If a user had many months of data, unnecessary monthly objects were
            # read, moved, and processed before being discarded.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Use aggregation with $match followed by $project and $filter on
            # parsedMonthDate. Only requested months continue through the pipeline.
            # This reduces BSON movement, aggregation CPU usage, and memory usage.
            #
            ############################################################
            {
                "$match": {
                    "user_id": user_id
                }
            },
            {
                "$project": {
                    "user_id": 1,
                    "account_details":1,
                    "summary": {
                        "$filter": {
                            "input": {
                                "$ifNull": [
                                    "$analysis_metadata.Data.Summary Of Debit And Credit",
                                    []
                                ]
                            },
                            "as": "summary",
                            "cond": {
                                "$and": [
                                    {
                                        "$gte": [
                                            "$$summary.parsedMonthDate",
                                            normalized_from
                                        ]
                                    },
                                    {
                                        "$lte": [
                                            "$$summary.parsedMonthDate",
                                            normalized_to
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                }
            },

            ############################################################
            #
            # EXISTING PROBLEM
            #
            # The previous pipeline unwound the entire monthly array before applying
            # the date filter. For a document containing 60 months, MongoDB created
            # 60 intermediate documents even when only 3 months were requested.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Filter the array first using parsedMonthDate, then unwind only the
            # required months. This significantly reduces intermediate documents,
            # aggregation CPU usage, memory usage, and BSON movement.
            #
            ############################################################
            {
                "$unwind": "$summary"
            },

            ############################################################
            #
            # EXISTING PROBLEM
            #
            # Chronological ordering must be preserved for monthly output. Sorting
            # after unnecessary expansion makes MongoDB sort more rows than needed.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Sort the already-filtered monthly rows by parsedMonthDate before
            # grouping. The $push in the group stage preserves that sorted order
            # while sorting a smaller working set.
            #
            ############################################################
            {
                "$sort": {
                    "summary.parsedMonthDate": 1
                }
            },

            ############################################################
            #
            # EXISTING PROBLEM
            #
            # The previous implementation repeatedly accessed the long field path
            # analysis_metadata.Data.Summary Of Debit And Credit in many expressions.
            # Long repeated paths make the pipeline harder to maintain and add
            # repeated path traversal work.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Alias the filtered monthly object as summary and reuse that alias.
            # This keeps expressions compact and avoids repeatedly traversing the
            # original nested field path.
            #
            ############################################################
            #
            # EXISTING PROBLEM
            #
            # Numeric fields were converted repeatedly with $toDouble and $ifNull
            # for monthly totals, monthly breakdowns, and overall totals.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Convert every required numeric value exactly once. Downstream stages
            # reuse converted fields, reducing aggregation CPU and duplicated
            # expression evaluation.
            #
            ############################################################
            {
                "$project": {
                    "user_id": 1,
                    "account_details":"$account_details",
                    "month": "$summary.month",
                    "parsedMonthDate": "$summary.parsedMonthDate",
                    "cash_deposit": {
                        "$toDouble": {"$ifNull": ["$summary.cashdeposit", "0"]}
                    },
                    "cheque_receipt": {
                        "$toDouble": {"$ifNull": ["$summary.chequeReceipt", "0"]}
                    },
                    "online_receipt": {
                        "$toDouble": {"$ifNull": ["$summary.onlineReceipt", "0"]}
                    },
                    "other_receipt": {
                        "$toDouble": {"$ifNull": ["$summary.otherRecipt", "0"]}
                    },
                    "inhouse_receipt": {
                        "$toDouble": {"$ifNull": ["$summary.inhouseRecipt", "0"]}
                    },
                    "cash_deposit_no": {
                        "$toDouble": {"$ifNull": ["$summary.cashdepositNo", 0]}
                    },
                    "cheque_receipt_no": {
                        "$toDouble": {"$ifNull": ["$summary.chequeReceiptNo", 0]}
                    },
                    "online_receipt_no": {
                        "$toDouble": {"$ifNull": ["$summary.onlineReceiptNo", 0]}
                    },
                    "other_receipt_no": {
                        "$toDouble": {"$ifNull": ["$summary.otherReciptNo", 0]}
                    },
                    "inhouse_receipt_no": {
                        "$toDouble": {"$ifNull": ["$summary.inhouseReciptNo", 0]}
                    },
                    "cash_withdrawal": {
                        "$toDouble": {"$ifNull": ["$summary.cashwithDraw", "0"]}
                    },
                    "cheque_payment": {
                        "$toDouble": {"$ifNull": ["$summary.chequePayment", "0"]}
                    },
                    "online_payment": {
                        "$toDouble": {"$ifNull": ["$summary.onlinePayment", "0"]}
                    },
                    "other_payment": {
                        "$toDouble": {"$ifNull": ["$summary.otherPayment", "0"]}
                    },
                    "inhouse_payment": {
                        "$toDouble": {"$ifNull": ["$summary.inhousePayment", "0"]}
                    },
                    "cash_withdrawal_no": {
                        "$toDouble": {"$ifNull": ["$summary.cashwithDrawNo", 0]}
                    },
                    "cheque_payment_no": {
                        "$toDouble": {"$ifNull": ["$summary.chequePaymentNo", 0]}
                    },
                    "online_payment_no": {
                        "$toDouble": {"$ifNull": ["$summary.onlinePaymentNo", 0]}
                    },
                    "other_payment_no": {
                        "$toDouble": {"$ifNull": ["$summary.otherPaymentNo", 0]}
                    },
                    "inhouse_payment_no": {
                        "$toDouble": {"$ifNull": ["$summary.inhousePaymentNo", 0]}
                    }
                }
            },

            ############################################################
            #
            # EXISTING PROBLEM
            #
            # Breakdown objects were rebuilt separately from the calculations that
            # produced totals. This duplicated expression work and increased the
            # chance of monthly and total logic drifting apart.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Create reusable breakdown objects from the converted numeric fields
            # once, then reuse those objects in monthly output and overall totals.
            # This reduces CPU work and keeps the response fields consistent.
            #
            ############################################################
            #
            # EXISTING PROBLEM
            #
            # Adjacent $project and $addFields style transformations can carry
            # extra fields through the pipeline and make each stage do more work
            # than necessary.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Merge compatible shaping work into compact $project stages and keep
            # only fields needed by later stages. This lowers memory pressure
            # between pipeline stages.
            #
            ############################################################
            {
                "$project": {
                    "user_id": 1,
                    "account_details":"$account_details",
                    "month": 1,
                    "parsedMonthDate": 1,
                    "mw_inflow_val": {
                        "$add": [
                            "$cash_deposit",
                            "$cheque_receipt",
                            "$online_receipt",
                            "$other_receipt",
                            "$inhouse_receipt"
                        ]
                    },
                    "mw_inflow_val_breakdown": {
                        "cash_deposit": "$cash_deposit",
                        "cheque_receipt": "$cheque_receipt",
                        "online_receipt": "$online_receipt",
                        "other_receipt": "$other_receipt",
                        "inhouse_receipt": "$inhouse_receipt"
                    },
                    "mw_inflow_no": {
                        "$add": [
                            "$cash_deposit_no",
                            "$cheque_receipt_no",
                            "$online_receipt_no",
                            "$other_receipt_no",
                            "$inhouse_receipt_no"
                        ]
                    },
                    "mw_inflow_no_breakdown": {
                        "cash_deposit_no": "$cash_deposit_no",
                        "cheque_receipt_no": "$cheque_receipt_no",
                        "online_receipt_no": "$online_receipt_no",
                        "other_receipt_no": "$other_receipt_no",
                        "inhouse_receipt_no": "$inhouse_receipt_no"
                    },
                    "mw_outflow_val": {
                        "$add": [
                            "$cash_withdrawal",
                            "$cheque_payment",
                            "$online_payment",
                            "$other_payment",
                            "$inhouse_payment"
                        ]
                    },
                    "mw_outflow_val_breakdown": {
                        "cash_withdrawal": "$cash_withdrawal",
                        "cheque_payment": "$cheque_payment",
                        "online_payment": "$online_payment",
                        "other_payment": "$other_payment",
                        "inhouse_payment": "$inhouse_payment"
                    },
                    "mw_outflow_no": {
                        "$add": [
                            "$cash_withdrawal_no",
                            "$cheque_payment_no",
                            "$online_payment_no",
                            "$other_payment_no",
                            "$inhouse_payment_no"
                        ]
                    },
                    "mw_outflow_no_breakdown": {
                        "cash_withdrawal_no": "$cash_withdrawal_no",
                        "cheque_payment_no": "$cheque_payment_no",
                        "online_payment_no": "$online_payment_no",
                        "other_payment_no": "$other_payment_no",
                        "inhouse_payment_no": "$inhouse_payment_no"
                    }
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "account_details": {"$first": "$account_details"},
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
                            "outflows_no_breakdown": "$mw_outflow_no_breakdown"
                        }
                    },
                    "total_Inflows_VALUE": {"$sum": "$mw_inflow_val"},
                    "total_Inflows_NO": {"$sum": "$mw_inflow_no"},
                    "total_Outflows_VALUE": {"$sum": "$mw_outflow_val"},
                    "total_Outflows_NO": {"$sum": "$mw_outflow_no"},
                    "total_cash_deposit_val": {"$sum": "$mw_inflow_val_breakdown.cash_deposit"},
                    "total_cheque_receipt_val": {"$sum": "$mw_inflow_val_breakdown.cheque_receipt"},
                    "total_online_receipt_val": {"$sum": "$mw_inflow_val_breakdown.online_receipt"},
                    "total_other_receipt_val": {"$sum": "$mw_inflow_val_breakdown.other_receipt"},
                    "total_inhouse_receipt_val": {"$sum": "$mw_inflow_val_breakdown.inhouse_receipt"},
                    "total_cash_deposit_no": {"$sum": "$mw_inflow_no_breakdown.cash_deposit_no"},
                    "total_cheque_receipt_no": {"$sum": "$mw_inflow_no_breakdown.cheque_receipt_no"},
                    "total_online_receipt_no": {"$sum": "$mw_inflow_no_breakdown.online_receipt_no"},
                    "total_other_receipt_no": {"$sum": "$mw_inflow_no_breakdown.other_receipt_no"},
                    "total_inhouse_receipt_no": {"$sum": "$mw_inflow_no_breakdown.inhouse_receipt_no"},
                    "total_cash_withdraw_val": {"$sum": "$mw_outflow_val_breakdown.cash_withdraw"},
                    "total_cheque_payment_val": {"$sum": "$mw_outflow_val_breakdown.cheque_payment"},
                    "total_online_payment_val": {"$sum": "$mw_outflow_val_breakdown.online_payment"},
                    "total_other_payment_val": {"$sum": "$mw_outflow_val_breakdown.other_payment"},
                    "total_inhouse_payment_val": {"$sum": "$mw_outflow_val_breakdown.inhouse_payment"},
                    "total_cash_withdraw_no": {"$sum": "$mw_outflow_no_breakdown.cash_withdrawal_no"},
                    "total_cheque_payment_no": {"$sum": "$mw_outflow_no_breakdown.cheque_payment_no"},
                    "total_online_payment_no": {"$sum": "$mw_outflow_no_breakdown.online_payment_no"},
                    "total_other_payment_no": {"$sum": "$mw_outflow_no_breakdown.other_payment_no"},
                    "total_inhouse_payment_no": {"$sum": "$mw_outflow_no_breakdown.inhouse_payment_no"}
                }
            },

            ############################################################
            #
            # EXISTING PROBLEM
            #
            # The previous implementation returned raw grouped data and then used
            # Python loops to lowercase month names and rebuild the frontend JSON
            # shape.
            #
            ############################################################
            #
            # SOLUTION
            #
            # Push response formatting into MongoDB with a final $project and $map.
            # The application can return result[0] directly, reducing Python CPU
            # usage and application memory allocation.
            #
            ############################################################
            {
                "$project": {
                    "_id": 1,
                    "account_details":"$account_details",
                    "monthly_breakdown": {
                        "$map": {
                            "input": "$monthly_breakdown",
                            "as": "entry",
                            "in": {
                                "month": {"$toLower": "$$entry.month"},
                                "inflows_value": {
                                    "inflows_value_breakdown": "$$entry.inflows_value_breakdown",
                                    "total_receipt_inflows_value": "$$entry.total_Inflows_VALUE"
                                },
                                "inflows_no": {
                                    "inflows_no_breakdown": "$$entry.inflows_no_breakdown",
                                    "total_receipt_inflows_no": "$$entry.total_Inflows_NO"
                                },
                                "outflows_value": {
                                    "outflows_value_breakdown": "$$entry.outflows_value_breakdown",
                                    "total_payments_outflows_value": "$$entry.total_Outflows_VALUE"
                                },
                                "outflows_no": {
                                    "outflows_no_breakdown": "$$entry.outflows_no_breakdown",
                                    "total_payments_outflows_no": "$$entry.total_Outflows_NO"
                                }
                            }
                        }
                    },
                    "total": {
                        "total_receipt_inflows_value": "$total_Inflows_VALUE",
                        "total_receipt_inflows_no": "$total_Inflows_NO",
                        "total_payments_outflows_value": "$total_Outflows_VALUE",
                        "total_payments_outflows_no": "$total_Outflows_NO",
                        "inflows_value_breakdown": {
                            "cash_deposit": "$total_cash_deposit_val",
                            "cheque_receipt": "$total_cheque_receipt_val",
                            "online_receipt": "$total_online_receipt_val",
                            "other_receipt": "$total_other_receipt_val",
                            "inhouse_receipt": "$total_inhouse_receipt_val"
                        },
                        "inflows_no_breakdown": {
                            "cash_deposit": "$total_cash_deposit_no",
                            "cheque_receipt": "$total_cheque_receipt_no",
                            "online_receipt": "$total_online_receipt_no",
                            "other_receipt": "$total_other_receipt_no",
                            "inhouse_receipt": "$total_inhouse_receipt_no"
                        },
                        "outflows_value_breakdown": {
                            "cash_withdrawal": "$total_cash_withdraw_val",
                            "cheque_payment": "$total_cheque_payment_val",
                            "online_payment": "$total_online_payment_val",
                            "other_payment": "$total_other_payment_val",
                            "inhouse_payment": "$total_inhouse_payment_val"
                        },
                        "outflows_no_breakdown": {
                            "cash_withdrawal_no": "$total_cash_withdraw_no",
                            "cheque_payment_no": "$total_cheque_payment_no",
                            "online_payment_no": "$total_online_payment_no",
                            "other_payment_no": "$total_other_payment_no",
                            "inhouse_payment_no": "$total_inhouse_payment_no"
                        }
                    }
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

        total_time = time.perf_counter() - start_time
        logger.info("total_time | user_id=%s | %.2fs", user_id, total_time)
        return result[0]
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



async def get_r1xcrm_summary_of_debit_and_credit_monthwise(db,acc_id: int,from_date,to_date) -> dict:
    if not acc_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "account id is required"}
        )
    user = await db["users"].find_one({"account_id": acc_id})
    print(user["_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "account is not registered as user"}
        )
    return await bsa_summary_of_debit_credit_monthwise(db, str(user["_id"]),from_date,to_date)