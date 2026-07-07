"""
Eligibility Service

This module evaluates a customer's bank statement parameters against
each bank's underwriting rules and determines eligibility.
"""

from fastapi.responses import JSONResponse
from starlette import status
from utils.aggregation import aggregate_parameter
from utils.tenure import calculate_threshold
from utils.comparator import compare


async def check_eligibility(request):
    """
    Evaluate customer eligibility across all banks.

    Flow:
        1. Fetch customer's BSA report. -> bsa_merged_bankstatements collection - 404 otherwise
        2. Extract all parameter sections (Overview, Cash Flow, etc.). 
        3. Iterate through each bank.
        4. Evaluate every underwriting rule.
        5. Compute score and eligibility.
        6. Return eligible and rejected banks.

    Returns:
        JSONResponse
    """
    totalAverageCreditTranx=0;
    db = request.app.state.mongo_db
    user_id = request.state.user_id

    eligible_banks = []
    rejected_banks = []

    # Fetch customer's merged BSA report
    bsa_data = await db.bsa_merged_bankstatements.find_one({"user_id": user_id})


    if not bsa_data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "BSA report not found."}
        )

    # Extract all analysis sections.
    # Additional sections (GST, ITR, EOD, etc.) can easily be added here.
    data = bsa_data.get("analysis_metadata", {}).get("Data", {})

    customer_sections = {
        "OverView": data.get("OverView", []),
        "Cash Flow": data.get("Cash Flow", [])
    }

    if not customer_sections["OverView"]:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Overview metrics not found."}
        )

    # Number of months available in customer's BSA
    customer_tenure = len(customer_sections["OverView"])

    banks = await db.banks.find().to_list(None)

    for bank in banks:

        # Fetch underwriting rules of the bank
        bank_rules = await db.bank_parameters.find_one({"bank_id": bank["_id"]})

        if not bank_rules:
            continue

        passed = 0
        failed = 0
        passed_parameters = []
        failed_parameters = []

        # Evaluate every parameter configured for this bank
        for parameter, rule in bank_rules["parameters"].items():

            aggregation = rule.get("aggregation", "latest")

            customer_value = aggregate_parameter(
                customer_sections,
                parameter,
                aggregation
            )

            # Parameter not available in customer's BSA
            if customer_value is None:

                if rule.get("mandatory", False):
                    failed += 1
                    failed_parameters.append({
                        "parameter": parameter,
                        "reason": "Parameter missing"
                    })

                continue

            # print(f"Customer value : {customer_value} | Bank-value {rule.get('value')} \n parameter: {parameter}")
            
            if parameter == "AverageCreditTranx":
                totalAverageCreditTranx+=customer_value;
                print(f"Total Average Credit Transactions : {totalAverageCreditTranx} \n parameter: {parameter}")
            # Calculate threshold based on tenure rules
            threshold = calculate_threshold(rule, customer_tenure)

            # Customer does not satisfy minimum tenure requirement
            if threshold is None:
                failed += 1
                failed_parameters.append({
                    "parameter": parameter,
                    "reason": f"Minimum tenure required is {rule['min_tenure']} months"
                })
                continue

            # Compare customer value against bank rule
            if compare(customer_value, rule["operator"], threshold):

                passed += 1
                passed_parameters.append({
                    "parameter": parameter,
                    "customer_value": customer_value,
                    "expected": f"{rule['operator']} {threshold}"
                })

            else:

                failed += 1
                failed_parameters.append({
                    "parameter": parameter,
                    "customer_value": customer_value,
                    "expected": f"{rule['operator']} {threshold}"
                })

        total = passed + failed
        score = round((passed / total) * 100, 2) if total else 0

        result = {
            "bank_id": str(bank["_id"]),
            "bank_name": bank["bank_name"],
            "eligibility": "Eligible" if score >= 50 else "Ineligible",
            "passed": passed,
            "failed": failed,
            "score": score,
            "passed_parameters": passed_parameters,
            "failed_parameters": failed_parameters
        }

        if score >= 30:
            eligible_banks.append(result)
        else:
            rejected_banks.append(result)

    return JSONResponse(
        status_code=200,
        content={
            "eligible_banks": eligible_banks,
            "rejected_banks": rejected_banks
        }
    )