from ..models import Coupon, CouponUsage, D, Role, q2, utcnow


class CouponError(Exception):
    pass


def validate_coupon(code, user, subtotal):
    coupon = Coupon.query.filter_by(code=code.strip().upper(), active=True).first()
    if not coupon:
        raise CouponError("Invalid or inactive coupon code.")
    now = utcnow()
    if coupon.start_date and now < coupon.start_date:
        raise CouponError("This coupon is not active yet.")
    if coupon.expiry_date and now > coupon.expiry_date:
        raise CouponError("This coupon has expired.")
    if coupon.customers_only and user.role != Role.CUSTOMER:
        raise CouponError("This coupon is valid for retail customers only.")
    if coupon.min_order and D(subtotal) < D(coupon.min_order):
        raise CouponError(f"Minimum order of ₹{coupon.min_order} required for this coupon.")
    if coupon.usage_limit and coupon.usages.count() >= coupon.usage_limit:
        raise CouponError("This coupon has reached its usage limit.")
    if coupon.per_user_limit:
        used = coupon.usages.filter_by(user_id=user.id).count()
        if used >= coupon.per_user_limit:
            raise CouponError("You have already used this coupon.")
    return coupon


def compute_discount(coupon, subtotal):
    subtotal = D(subtotal)
    if coupon.discount_type == "PERCENT":
        amount = subtotal * D(coupon.discount_value) / D(100)
        if coupon.max_discount:
            amount = min(amount, D(coupon.max_discount))
    else:
        amount = D(coupon.discount_value)
    return q2(min(amount, subtotal))
