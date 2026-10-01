"""Clean sample code: well-factored, should pass a CodeSage review."""

MAX_ITEMS = 100


def add(first, second):
    """Return the sum of two numbers."""
    return first + second


def average(values):
    """Return the mean of a list of numbers."""
    total = 0
    count = 0
    for value in values:
        total += value
        count += 1
    return total / count


def is_valid(items):
    """Return True when the item list is non-empty and within limits."""
    if not items:
        return False
    return len(items) <= MAX_ITEMS
