from statistics import mean


def aggregate_parameter(customer_sections, parameter, aggregation):
    """
    Aggregate a customer parameter across all available BSA sections.

    Args:
        customer_sections (dict):
            Dictionary containing BSA sections.
            Example:
            {
                "OverView": [...],
                "Cash Flow": [...]
            }

        parameter (str):
            Bank parameter to evaluate.

        aggregation (str):
            Aggregation strategy.
            Supported values:
                - latest
                - sum
                - average

    Returns:
        float | None:
            Aggregated customer value.
            Returns None if the parameter is not found.
    """

    values = []
    section_name = None

    # Find the section that contains the parameter
    for name, records in customer_sections.items():

        if not records:
            continue

        if parameter not in records[0]:
            continue

        section_name = name
        print(f"Parameter '{parameter}' found in section '{section_name}'")
        for record in records:

            value = record.get(parameter)

            if value is None or value == "":
                continue

            # Cash Flow values are stored as strings
            if isinstance(value, str):
                value = float(value.replace(",", ""))

            values.append(value)

        break

    if not values:
        return None

    if aggregation == "sum":
        result = sum(values)

    elif aggregation == "average":
        result = mean(values)

    elif aggregation == "latest":
        result = values[-1]

    else:
        raise ValueError(
            f"Unsupported aggregation type: {aggregation}"
        )

    # Overview values are stored in lakhs.
    # Convert them to rupees before comparison.
    if section_name == "OverView":
        result *= 100000

    return result