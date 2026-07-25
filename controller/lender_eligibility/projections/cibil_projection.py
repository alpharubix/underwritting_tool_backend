def get_cibil_projection(user_id) -> list:
    EQUIFAX_DATA = "cibil_report.EquifaxRetail"
    
    return [

        {
            "$match":{
                "user_id":user_id
            }
        },
        {
            "$project": {
                "_id":0,
                "score": f"${EQUIFAX_DATA}.BureauAnalysis.score",
                #exact match not found - days_past
                "days_past_due_active": {
                    "$convert": {
                        "input": f"${EQUIFAX_DATA}.generalInfo.repaymentObligations.dpdsinActiveAccounts",
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                },

                #       
                "default_rate_%": {
                    "$convert": {
                        "input": f"${EQUIFAX_DATA}.generalInfo.repaymentObligations.totalnoofDPDsrecorded",
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                },
                # "default_delay_rate": f"${EQUIFAX_DATA}.ScoremeAnalysis.total.percentofdelaytotal",
                "total_enquiries": {
                    "$convert": {
                        "input": f"${EQUIFAX_DATA}.generalInfo.enquiries.totalEnquiries",
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                },
                "business_loan_accounts": {
                    "$convert": {
                        "input": f"${EQUIFAX_DATA}.generalInfo.accountType.businessLoan.totalAccount",
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                }
            }
        }
    ]