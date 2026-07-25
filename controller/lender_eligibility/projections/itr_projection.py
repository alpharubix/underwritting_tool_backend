def get_itr_projection(user_id) -> list:
    DATA = "report.Profit And Loss Statement.Profit and Loss Statement"
    RATIO_COVERAGE = "report.Ratio Analysis.Coverage Ratios"
    RATIO_LEVERAGE = "report.Ratio Analysis.Leverage Ratios"
    RATIO_LIQUIDITY = "report.Ratio Analysis.Liquidity Analysis"
    
    return [
        {
            "$match":{
                "user_id":user_id
            }
        },
        {
            "$project": {
                "_id":0,
                "profit_after_tax": {
                    "$arrayElemAt":[
                        f"${DATA}.Profit after Tax"
                    ,-1]
                },
                "revenue_from_operations":{
                    "$arrayElemAt":[
                         f"${DATA}.Revenue from Operations",-1
                    ]
                },
                "interest_coverage_ratio": {
                    "$convert": {
                        "input": {
                            "$arrayElemAt": [
                                f"${RATIO_COVERAGE}.Interest Coverage Ratio",
                                -1
                            ]
                        },
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                },
                "current_ratio": {
                        "$arrayElemAt":[
                            f"${RATIO_LIQUIDITY}.Current Ratio",-1
                        ]
                },
                "debt_equity_ratio":{
                    "$convert": {
                        "input": {
                            "$arrayElemAt": [
                                f"${RATIO_LEVERAGE}.Debt Equity Ratio",
                                -1
                            ]
                        },
                        "to": "double",
                        "onError": None,
                        "onNull": None
                    }
                }
            }
        }
    ]