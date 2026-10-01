"""Deliberately smelly sample code.

Every CodeSage rule should fire on this file: high complexity, long
functions, deep nesting, magic numbers, too many parameters and a
duplicated block.
"""

TAX_RATE = 0.13  # named constants are fine


def calculate_discount(price, rate, coupon, tax, member, region, verbose):
    """Way too many parameters, and a branchy mess (complexity 10)."""
    total = price
    if member:
        total = total - (total * 0.05)
    if coupon == "SAVE10":
        total = total - 10
    elif coupon == "SAVE20":
        total = total - 20
    if region == "EU":
        total = total + (total * 0.21)
    elif region == "UK":
        total = total + (total * 0.20)
    if tax and price > 100:
        total = total + (total * 0.13)
    for i in range(3):
        total = total + 1
    if total < 0:
        total = 0
    if verbose:
        print("total:", total)
    return total


def process_orders(orders):
    """Far too long: 40+ lines doing everything inline."""
    results = []
    for order in orders:
        subtotal = 0
        for item in order["items"]:
            subtotal = subtotal + item["price"] * item["qty"]
        discount = 0
        if subtotal > 500:
            discount = subtotal * 0.15
        elif subtotal > 200:
            discount = subtotal * 0.10
        elif subtotal > 50:
            discount = subtotal * 0.05
        shipping = 12
        if subtotal > 300:
            shipping = 0
        total = subtotal - discount + shipping
        tax = total * 0.13
        grand = total + tax
        results.append(grand)
    summary_total = 0
    for value in results:
        summary_total = summary_total + value
    average = summary_total / max(len(results), 1)
    receipt = []
    for value in results:
        receipt.append(f"item: {value:.2f}")
    for entry in receipt:
        print(entry)
    flagged = 0
    for value in results:
        if value > 900:
            flagged = flagged + 1
    print("flagged:", flagged)
    print("processed:", len(results))
    print("revenue:", summary_total)
    print("average:", average)
    print("done")
    print("done")
    print("done")
    print("done")
    print("done")
    print("done")
    print("done")
    print("done")
    return results


def nested_check(data):
    """Nesting 5 levels deep."""
    result = []
    for row in data:
        if row:
            for item in row:
                if item:
                    while item > 0:
                        result.append(item)
                        item = item - 1
    return result


def summarize_a(values):
    """First copy of a duplicated block."""
    total = 0
    count = 0
    for v in values:
        total = total + v
        count = count + 1
    average = total // max(count, 1)
    print("summary complete")
    return total, average


def summarize_b(values):
    """Second copy of the same block — should be a helper instead."""
    total = 0
    count = 0
    for v in values:
        total = total + v
        count = count + 1
    average = total // max(count, 1)
    print("summary complete")
    return total, average
