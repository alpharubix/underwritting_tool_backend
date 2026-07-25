from controller.lender_eligibility.projections.bsa_projection import get_bsa_projection
from controller.lender_eligibility.projections.cibil_projection import get_cibil_projection
from controller.lender_eligibility.projections.gst_projection import get_gst_projection
from controller.lender_eligibility.projections.itr_projection import get_itr_projection
from controller.lender_eligibility.projections.lender_projection import get_lender_projection
from fastapi import Request
import time
import asyncio
start = time.perf_counter()

def calculate(lender_val,cust_val,op)->bool:
    if op=="=":
        return cust_val==lender_val
    elif op==">=":
        return cust_val>=lender_val
    else:
        return cust_val<=lender_val

# HELPER FUNCTION - BELOW 
def get_failed_reason(op, cust_val, lender_val, parameter_key) -> str:
    if op == ">=":
        return f"{parameter_key}: Min {lender_val}, Found {cust_val}, Short by {lender_val - cust_val}"

    elif op == "<=":
        return f"{parameter_key}: Max {lender_val}, Found {cust_val}, Exceeded by {cust_val - lender_val}"

    return f"{parameter_key}: Expected {op} {lender_val}, Found {cust_val}"

#for checking cust_val and lend_val | parameter wise checking function
def evaluate(customer_metrics:dict,lender_metrics:list[dict]) -> list:
    message=[]
    passed = 0
    failed = 0
    
    for lender in lender_metrics:
        failed_message=[]
        passed_parameters = []
        failed_parameters = []
        bank_name = lender.get("bank_name")
        bank_code = lender.get("bank_code")
        passed=0
        failed=0
        
        for parameter in lender["parameters"]:
            parameter_key = parameter.get("parameter_key")
            op = parameter.get("operator")
            lender_val = parameter.get("threshold")
            cust_val = customer_metrics.get(parameter_key)
    
            if cust_val is None:
                failed+=1
                failed_message.append(
                    {
                        "parameter_key":parameter_key,
                        "reason":"Customer value for this parameter is not available.",
                        "cust_val":None,
                        "status":"NOT ELIGIBLE",
                        "operator":op,
                        "lender_val":lender_val
                    }
                )
                
                continue

            result = calculate(lender_val, cust_val, op)
            score = 0

            #result is False - > when criteria failed -> ineligibile 
            if result == False:
                reason=  get_failed_reason(op,cust_val,lender_val,parameter_key)
                failed+=1
                failed_parameters.append(parameter_key)
                failed_message.append(
                    {
                        "parameter_key":parameter_key,
                        "status":"NOT ELIGIBLE",
                        "reason": reason,
                        "cust_val":cust_val,
                        "operator":op,
                        "lender_val":lender_val
                    }
                )
                
                continue
            passed+=1
            passed_parameters.append(parameter_key)
    

        score = (passed/(passed+failed) )*100
        message.append(
            {
                "bank_name":bank_name,
                "bank_code":bank_code,
                "no_failed_parameters":failed,
                "no_passed_parameters":passed,
                "eligibility_score":round(score,2),
                "eligibility":"waiting for ashok anna to give the eligibility number",
                "failed_parameters":failed_parameters,
                "passed_parameters":passed_parameters,
                "reason":failed_message
            }
        )

    return message

#MAIN CONTROLLER
async def get_lender_eligibility(request:Request):
    user_id=request.state.user_id

    db = request.app.state.mongo_db

    # only collections 
    lender_col = db["lender_profiles"]
    bsa_col = db["bsa_merged_bankstatements"]
    gst_col = db["gst_analyzed_report"]
    itr_col = db["itr_analyzed_report"]
    cibil_col = db["cibil_report"]

    # pipelines
    lender_pipeline = get_lender_projection()
    bsa_pipeline = get_bsa_projection(user_id)
    gst_pipeline = get_gst_projection(user_id)
    itr_pipeline = get_itr_projection(user_id)
    cibil_pipeline = get_cibil_projection(user_id)
    #result - object form 
    # t=time.perf_counter()
    # lender_result = await lender_col.aggregate(lender_pipeline).to_list(length=None)
    # print(f"LENDER: {time.perf_counter() - t:.3f}s")
    # t = time.perf_counter()
    # bsa_result = await bsa_col.aggregate(bsa_pipeline).to_list(length=None)
    # print(f"BSA: {time.perf_counter() - t:.3f}s")
    # t = time.perf_counter()
    # gst_result = await gst_col.aggregate(gst_pipeline).to_list(length=None)
    # print(f"GST: {time.perf_counter() - t:.3f}s")
    # t = time.perf_counter()
    # itr_result = await itr_col.aggregate(itr_pipeline).to_list(length=None)
    # print(f"ITR: {time.perf_counter() - t:.3f}s")
    # t = time.perf_counter()
    # cibil_result = await cibil_col.aggregate(cibil_pipeline).to_list(length=None)
    # print(f"CIBIL: {time.perf_counter() - t:.3f}s")


    # MONGO ENHANCEMENT - 
    # Data gathering from collection after applying the projection
    lender_result, bsa_result, gst_result, itr_result, cibil_result = await asyncio.gather(
        lender_col.aggregate(lender_pipeline).to_list(None),
        bsa_col.aggregate(bsa_pipeline).to_list(None),
        gst_col.aggregate(gst_pipeline).to_list(None),
        itr_col.aggregate(itr_pipeline).to_list(None),
        cibil_col.aggregate(cibil_pipeline).to_list(None),
    )

    # print("GST RESULT:", gst_result)
    bsa_metrics = bsa_result[0] if bsa_result else {}
    gst_metrics = gst_result[0] if gst_result else {}
    itr_metrics = itr_result[0] if itr_result else {}
    cibil_metrics = cibil_result[0] if cibil_result else {}

    print("BSA RESULT : ",bsa_metrics)
    # print("Cust  result[0] : ",gst_metrics)
    


    customer_metrics = {
        **bsa_metrics,
        **gst_metrics,
        **itr_metrics,
        **cibil_metrics
    }
    
    
    data = evaluate(customer_metrics,lender_result)
    return data
