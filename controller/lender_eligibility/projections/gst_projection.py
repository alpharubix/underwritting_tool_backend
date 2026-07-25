def get_gst_projection(user_id):
    SNAPSHOT_DATA = "report.Snapshot.Averages"
    OVERVIEW_GST_RETURNS_DATA = "report.Overview.Overview of GST Returns"
    
    return [
        {
            "$match":{
                "user_id":user_id
            },
        },
        {
            
            "$project": {
                "_id":0,
                "debug_gstr1": {
                "$getField": {
                    "field": "GSTR 1",
                    "input": {
                        "$first": {
                            "$first": f"${OVERVIEW_GST_RETURNS_DATA}"
                        }
                    }
                }
                },
                "created_at":"$created_at",
                "average_sales_per_month": {
                    "$convert":{
                        "input":{
                            "$getField": {
                                "field": "Average Sales per Month",
                                "input": {
                                    "$first": {
                                        "$first": f"${SNAPSHOT_DATA}"
                                    }
                                }
                            }
                        },
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                },

                "average_purchases_per_month": {
                    "$convert":{
                        "input":{
                            "$getField":{
                                "field":"Average Purchases per Month",
                                "input":{
                                "$first":{
                                    "$first":f"${SNAPSHOT_DATA}"
                                    }
                                }
                            }
                        },
                        "to":"double",
                        "onError": None,
                        "onNull": None
                    }
                },
                "gross_profit": {
                    "$convert":{
                        "input":{
                            "$getField": {
                                "field": "Gross Profit (K=E-J)",
                                "input": {
                                    "$getField": {
                                        "field": "Gross Profit",
                                        "input": {
                                            "$arrayElemAt": [
                                                {
                                                    "$first": {
                                                        "$first": f"${OVERVIEW_GST_RETURNS_DATA}"
                                                    }
                                                },
                                                2
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "to":"double",
                        "onError":None,
                        "onNull":None
                    }
                },
                "input_tax_credit_available": {
                    "$convert":{
                        "input":{
                            "$getField":{
                                "field":"Input Tax Credit Available(M)",
                                "input":{
                                    "$getField":{
                                        "field":"Input Tax Credit Available",
                                        "input":{
                                            "$arrayElemAt":[
                                                {
                                                    "$first":{
                                                        "$first":f"${OVERVIEW_GST_RETURNS_DATA}"
                                                    }
                                                },
                                                4
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "to":"double",
                        "onError": None,
                        "onNull": None
                    }
                },
                "total_value_of_sales": {
                    "$convert":{
                        "input":{
                            "$getField":{
                                "field":"Total Value of Sales (A)",
                                "input":{
                                    "$getField":{
                                        "field":"GSTR 1",
                                        "input": {
                                        "$arrayElemAt": [
                                            {
                                                "$first": {
                                                    "$first": f"${OVERVIEW_GST_RETURNS_DATA}"
                                                }
                                            },
                                            0
                                        ]
                                        }
                                    }
                                }
                            }
                        },
                        "to":"double",
                        "onError":None,
                        "onNull":None
                    }
                }
            }
        }

       
    
]
