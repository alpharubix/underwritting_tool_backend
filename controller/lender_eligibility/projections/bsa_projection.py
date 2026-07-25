from queue import Full

from database.db import get_mongo_db
# db = get_mongo_db()
def get_bsa_projection(user_id:any)->list:
    
    # bsa_collection = db["bsa_merged_bankstatements"]

    DATA = "$analysis_metadata.Data"

    OVERVIEW = f"{DATA}.OverView"
    return [
       {
          "$match":{"user_id":user_id}
       },
       {
           
           "$project":{
               #NOT A LAKH FIGURE - THIS SEEMS TO BE count
               "inward_cheque_return":{
                   "$sum":{
                       "$map":{
                           "input":OVERVIEW,
                           "as":"month",
                           "in":"$$month.InwardChequeReturnNos"
                       }
                   }
               },

                #LAKH FIGURE
                "net_cash_inflow":{
                    #review
                    "$multiply":[
                        {
                            "$min":{
                                "$map":{
                                    "input":OVERVIEW,
                                    "as":"month",
                                    "in":"$$month.NetCashInflow"
                                }
                            }
                        },
                        100000
                    ]
                },
                # IT IS PERCENT ? confirm 
                "average_od_cc_limit_utilization":{
                   "$avg":{
                       "$map":{
                           "input":OVERVIEW,
                           "as":"month",
                           "in":"$$month.AverageOdAndCCLimitUtilizationInPercent"
                       }
                   } 
                },
                #COUNT 
                "outward_cheque_return":{
                    "$sum":{
                        "$map":{
                            "input":OVERVIEW,
                            "as":"month",
                            "in":"$$month.OutwardChequeReturnNo"
                        }
                    }
                },

                #Average end of the day balance - seems to be LAKHS
                "average_eod":{
                    "$multiply":[{
                        "$avg":{
                            "$map":{
                                "input":OVERVIEW,
                                "as":"month",
                                "in":"$$month.AverageEod"
                            }
                        }
                },100000]    
                }

           }
       },
       {
        "$group": {
            "_id": None,
            "inward_cheque_return": {
                "$sum": "$inward_cheque_return"
            },
            "outward_cheque_return": {
                "$sum": "$outward_cheque_return"
            },
            "net_cash_inflow": {
                "$min": "$net_cash_inflow"
            },
            "average_od_cc_limit_utilization": {
                "$avg": "$average_od_cc_limit_utilization"
            },
            "average_eod": {
                "$avg": "$average_eod"
            }
        }
    }
  
   ]

