def get_lender_projection()->list:
    return[
        {
            "$project":{
                "_id":0,
                "bank_code":1,
                "bank_name":1,
                "parameters":1
            }
        }
    ]