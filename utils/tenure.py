def calculate_threshold(rule, customer_tenure):

    bank_value = float(rule["value"])

    minimum_tenure = rule.get("min_tenure", 1)

    scale = rule.get("scale_with_tenure", False)

    if customer_tenure < minimum_tenure:
        return None

    if scale:
        bank_value *= customer_tenure / minimum_tenure

    return bank_value