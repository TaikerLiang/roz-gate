def price(cart, now):
    """Sum item costs; an offer's discount applies while expires_at >= now (C1)."""
    total = 0
    for item in cart:
        offer = item.get("offer")
        if offer and offer["expires_at"] >= now:
            total += item["cost"] - offer["discount"]
        else:
            total += item["cost"]
    return total
