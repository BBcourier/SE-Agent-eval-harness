def median(values):
    if not values:
        raise ValueError("median() requires at least one value")

    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2

    if n % 2 == 1:
        return sorted_values[mid]

    return sorted_values[mid]