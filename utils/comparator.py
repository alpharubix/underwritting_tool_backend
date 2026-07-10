def compare(actual, operator, expected):
    if actual is None:
        return False

    if operator == ">=":
        return actual >= expected

    if operator == "<=":
        return actual <= expected

    if operator == ">":
        return actual > expected

    if operator == "<":
        return actual < expected

    if operator == "==":
        return actual == expected

    if operator == "!=":
        return actual != expected

    raise Exception(f"Unsupported operator : {operator}")