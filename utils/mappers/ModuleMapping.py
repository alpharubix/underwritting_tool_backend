from enum import Enum

class ModuleMapping(str, Enum):
    bsa = "bsa_merged_bankstatements"
    gst="gst_analyzed_report"
    itr = "itr_analyzed_report"
    cibil = "cibil_report"

class ModuleProjection(Enum):

    # bsa_previous = {
    #     "$project": {
    #         "_id": 0,

    #         "bsa_from_date": "$from_date",
    #         "bsa_to_date": "$to_date",

<<<<<<< Updated upstream
    #         "tenure": {
    #             "$add": [
    #                 {
    #                     "$dateDiff": {
    #                         "startDate": "$from_date",
    #                         "endDate": "$to_date",
    #                         "unit": "month"
    #                     }
    #                 },
    #                 1
    #             ]
    #         },
=======
            "tenure": {
                "$add": [
                    {
                        "$dateDiff": {
                            "startDate": "$from_date",
                            "endDate": "$to_date",
                            "unit": "month"
                        }
                    },
                ]
            },
>>>>>>> Stashed changes

    #         "generated_on": "$created_at"
    #     }
    # }

    gst = {
        "$project": {
            "_id": 0,
            "reference_id":1,
            "gst_from_date": {
                "$toString": {
                    "$arrayElemAt": [
                        "$report.Account Details.periodFrom",
                        0
                    ]
                }
            },
            "gst_to_date": {
                "$toString": {
                    "$arrayElemAt": [
                        "$report.Account Details.periodTo",
                        0
                    ]
                }
            },
            "generated_on": "$created_at",
        }
    }


    bsa={ # done - bsa_merged_bankstatements col -> looks fine
        "$project":{
            "_id":0,
            "bsa_from_date":"$from_date",
            "bsa_to_date":"$to_date",
            "last_merged_reference_id":1,
            "generated_on":"$created_at"
        }
    }
    itr = {
        "$project": {
            "_id": 0,
            "reference_id":1,
            "generated_on": "$created_at"
        }
    }

    cibil = {
        "$project": {
            "_id": 0,
            "reference_id":1,
            "generated_on": "$cibil_pulled_date"
        }
    }