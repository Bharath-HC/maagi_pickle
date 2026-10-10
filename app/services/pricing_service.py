from ..models import D, Role, q2


def price_field_for_role(role):
    return {
        Role.DISTRIBUTOR: "distributor_price",
        Role.WHOLESALER: "wholesaler_price",
    }.get(role, "customer_price")


def tier_for_role(role):
    return role if role in Role.B2B else Role.CUSTOMER


def variant_price(variant, role):
    field = price_field_for_role(role)
    value = getattr(variant, field, None)
    if not value:
        value = variant.customer_price
    return q2(value)


def savings(variant, role):
    price = variant_price(variant, role)
    mrp = D(variant.mrp)
    amount = max(D(0), mrp - price)
    percent = int((amount / mrp) * 100) if mrp > 0 else 0
    return {"amount": q2(amount), "percent": percent}


def moq_for(product, role):
    if role in Role.B2B:
        return max(1, product.minimum_order_quantity or 1)
    return 1
