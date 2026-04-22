import logging
import time
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from starlette import status
from datetime import datetime



logger=logging.getLogger(__name__)

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
    
    try:
        exists = await db.bankstatementreport.find_one({"user_id": str(user_id)}, {"_id": 1})
    except Exception as e:
        logger.error("preflight_failed | user_id=%s | error=%s", user_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Database error during preflight check"}
        )

    if not exists:
        logger.warning("report_not_found | user_id=%s", user_id)
        raise HTTPException(
            status_code=404,
            detail={"message": "Bank Statement Report not found for this user"}
        )
    
    try:
        docs_count=await db.bankstatementreport.count_documents({"user_id":str(user_id)})
        logger.info("Bank_statement_report |user_id=%s |docs_counts=%s",user_id,docs_count)
        pipeline=[
            # 1. Match only by user_id at document level
            {
                "$match": {
                    "user_id": user_id  # Use ObjectId(user_id) if stored as BSON
                }
            },

            # 2. Unwind all months across all documents
            {
                "$unwind": "$analysis_metadata.Data.Summary Of Debit And Credit"
            },

            # 3. Convert "Apr 2025" string → first day of that month as a real Date
            {
                "$addFields": {
                    "parsedMonthDate": {
                        "$dateFromString": {
                            "dateString": {
                                "$concat": [
                                    "01 ",
                                    "$analysis_metadata.Data.Summary Of Debit And Credit.month"
                                ]
                            },
                            "format": "%d %b %Y"
                        }
                    }
                }
            },

            # 4. NOW filter months that fall within the requested date range
            {
                "$match": {
                    "parsedMonthDate": {
                        "$gte": from_date,
                        "$lte": to_date
                    }
                }
            },

            # 5. Deduplicate: Latest document wins for duplicate months
            {
                "$sort": { "created_at": -1 }
            },
            {
                "$group": {
                    "_id": {
                        "user_id": "$user_id",
                        "month": "$analysis_metadata.Data.Summary Of Debit And Credit.month"
                    },
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
                    "parsedMonthDate": {
                        "$dateFromString": {
                            "dateString": { "$concat": ["01 ", "$_id.month"] },
                            "format": "%d %b %Y"
                        }
                    },
                    "mw_inflow_val": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashdeposit", "0"] } },
                            { "$toDouble": { "$ifNull": ["$chequeReceipt", "0"] } },
                            { "$toDouble": { "$ifNull": ["$onlineReceipt", "0"] } },
                            { "$toDouble": { "$ifNull": ["$otherRecipt", "0"] } },
                            { "$toDouble": { "$ifNull": ["$inhouseRecipt", "0"] } }
                        ]
                    },
                    "mw_inflow_no": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashdepositNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$chequeReceiptNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$onlineReceiptNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$otherReciptNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$inhouseReciptNo", 0] } }
                        ]
                    },
                    "mw_outflow_val": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashwithDraw", "0"] } },
                            { "$toDouble": { "$ifNull": ["$chequePayment", "0"] } },
                            { "$toDouble": { "$ifNull": ["$onlinePayment", "0"] } },
                            { "$toDouble": { "$ifNull": ["$otherPayment", "0"] } },
                            { "$toDouble": { "$ifNull": ["$inhousePayment", "0"] } }
                        ]
                    },
                    "mw_outflow_no": {
                        "$add": [
                            { "$toDouble": { "$ifNull": ["$cashwithDrawNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$chequePaymentNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$onlinePaymentNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$otherPaymentNo", 0] } },
                            { "$toDouble": { "$ifNull": ["$inhousePaymentNo", 0] } }
                        ]
                    }
                }
            },

            # 6b. Sort by month ascending
            {
                "$sort": {
                    "user_id": 1,
                    "parsedMonthDate": 1
                }
            },

            # 7. Final group by user
            {
                "$group": {
                    "_id": "$user_id",
                    "monthly_breakdown": {
                        "$push": {
                            "month": "$month",
                            "total_Inflows_VALUE": "$mw_inflow_val",
                            "total_Inflows_NO": "$mw_inflow_no",
                            "total_Outflows_VALUE": "$mw_outflow_val",
                            "total_Outflows_NO": "$mw_outflow_no"
                        }
                    },
                    "total_Inflows_VALUE":  { "$sum": "$mw_inflow_val" },
                    "total_Inflows_NO":       { "$sum": "$mw_inflow_no" },
                    "total_Outflows_VALUE": { "$sum": "$mw_outflow_val" },
                    "total_Outflows_NO":      { "$sum": "$mw_outflow_no" }
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
        return result[0]  # Return the summary for the user
    
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


            
        



