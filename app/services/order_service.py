from ..extensions import db
from ..models import (D, Order, OrderEvent, OrderItem, OrderStatus, PaymentMethod,
                      PaymentStatus, Role, q2, utcnow)
from . import coupon_service, inventory_service, pricing_service
from .audit_service import log_action
from .coupon_service import CouponError


class CheckoutError(Exception):
    pass


def _validate_lines(cart, user):
    if not cart.items:
        raise CheckoutError("Your cart is empty.")
    lines = []
    for item in cart.items:
        variant = item.variant
        product = variant.product
        if not variant.active or not product.active:
            raise CheckoutError(f"{product.name} ({variant.label}) is no longer available.")
        moq = pricing_service.moq_for(product, user.role)
        if item.quantity < moq:
            raise CheckoutError(f"Minimum order quantity for {product.name} is {moq}.")
        if item.quantity > variant.available_stock:
            raise CheckoutError(f"Only {variant.available_stock} unit(s) of {product.name} ({variant.label}) left in stock.")
        unit_price = pricing_service.variant_price(variant, user.role)
        gst_pct = D(product.gst_percentage or 0)
        line_subtotal = q2(unit_price * item.quantity)
        line_tax = q2(line_subtotal * gst_pct / D(100))
        lines.append({
            "product": product, "variant": variant, "quantity": item.quantity,
            "unit_price": unit_price, "mrp": D(variant.mrp), "gst_percentage": gst_pct,
            "subtotal": line_subtotal, "tax": line_tax, "sku": variant.sku,
        })
    return lines


def build_order_preview(cart, user, coupon_code=None):
    lines = _validate_lines(cart, user)
    subtotal = sum((l["subtotal"] for l in lines), start=D(0))
    tax = sum((l["tax"] for l in lines), start=D(0))

    coupon = None
    discount = D(0)
    coupon_error = None
    if coupon_code:
        try:
            coupon = coupon_service.validate_coupon(coupon_code, user, subtotal)
            discount = coupon_service.compute_discount(coupon, subtotal)
        except CouponError as exc:
            coupon_error = str(exc)
            coupon_code = None

    if user.role in Role.B2B:
        shipping = D(0)
    else:
        shipping = D(0) if subtotal >= D(999) else D(60)
        if subtotal <= 0:
            shipping = D(0)

    total = q2(subtotal - discount + tax + shipping)
    return {
        "lines": lines, "subtotal": q2(subtotal), "tax": q2(tax), "discount": q2(discount),
        "shipping": q2(shipping), "total": total, "coupon": coupon, "coupon_code": coupon_code,
        "coupon_error": coupon_error,
    }


def place_order(user, address, payment_method, coupon_code=None, notes=None, cart=None, source="WEB"):
    from .cart_service import clear_cart
    from ..utils.helpers import order_number

    preview = build_order_preview(cart, user, coupon_code)
    if preview["coupon_error"] and coupon_code:
        raise CheckoutError(preview["coupon_error"])
    if user.role in Role.B2B and payment_method == PaymentMethod.COD:
        raise CheckoutError("Cash on Delivery is not available for business accounts. Please pay online or use credit terms.")

    order = Order(
        order_number=order_number(), user_id=user.id, price_tier=pricing_service.tier_for_role(user.role),
        subtotal=preview["subtotal"], discount=preview["discount"], tax=preview["tax"],
        shipping_charge=preview["shipping"], total_amount=preview["total"],
        coupon_code=preview["coupon_code"], payment_method=payment_method,
        payment_status=PaymentStatus.PENDING, order_status=OrderStatus.PENDING,
        inventory_state="NONE", customer_name=address.name, customer_email=user.email,
        customer_phone=address.phone, company_name=user.company_name, gst_number=user.gst_number,
        shipping_address=address.as_text(), billing_address=address.as_text(), notes=notes, source=source,
    )
    db.session.add(order)
    db.session.flush()

    for line in preview["lines"]:
        db.session.add(OrderItem(
            order_id=order.id, product_id=line["product"].id, variant_id=line["variant"].id,
            product_name=line["product"].name, variant_label=line["variant"].label, sku=line["sku"],
            hsn_code=line["product"].hsn_code, gst_percentage=line["gst_percentage"], quantity=line["quantity"],
            mrp=line["mrp"], unit_price=line["unit_price"], tax=line["tax"], subtotal=line["subtotal"],
        ))
        inventory_service.reserve_stock(line["variant"], line["quantity"], order_id=order.id, user_id=user.id)

    order.inventory_state = "RESERVED"
    db.session.add(OrderEvent(order_id=order.id, status=OrderStatus.PENDING, note="Order placed", user_id=user.id))

    if preview["coupon"]:
        from ..models import CouponUsage
        db.session.add(CouponUsage(coupon_id=preview["coupon"].id, user_id=user.id, order_id=order.id,
                                   discount_amount=preview["discount"]))

    if payment_method in (PaymentMethod.COD, PaymentMethod.CREDIT):
        _finalize_confirmed(order, user)

    db.session.commit()
    clear_cart(cart)
    log_action("ORDER_PLACED", "Order", order.order_number, f"Total ₹{order.total_amount}")
    return order


def _finalize_confirmed(order, user=None):
    for item in order.items:
        inventory_service.deduct_stock(item.variant, item.quantity, order_id=order.id,
                                       user_id=user.id if user else None)
    order.inventory_state = "DEDUCTED"
    order.order_status = OrderStatus.CONFIRMED
    if order.payment_method in (PaymentMethod.COD, PaymentMethod.CREDIT):
        order.payment_status = PaymentStatus.PENDING if order.payment_method == PaymentMethod.CREDIT else order.payment_status
    from ..utils.helpers import invoice_number
    if not order.invoice_number:
        order.invoice_number = invoice_number()
    db.session.add(OrderEvent(order_id=order.id, status=OrderStatus.CONFIRMED, note="Order confirmed",
                              user_id=user.id if user else None))


def confirm_order_payment(order, mark_paid=True):
    if order.inventory_state != "DEDUCTED":
        _finalize_confirmed(order, order.user)
    if mark_paid:
        order.payment_status = PaymentStatus.PAID
    db.session.commit()
    log_action("ORDER_PAYMENT_CONFIRMED", "Order", order.order_number)
    from .notification_service import notify
    notify(order.user_id, "Payment received", f"We've received payment for order {order.order_number}.",
          "ORDER", f"/customer/orders/{order.order_number}")
    return order


def cancel_order(order, by_user=None, reason=None):
    if not order.can_cancel:
        raise CheckoutError("This order can no longer be cancelled.")
    for item in order.items:
        if order.inventory_state == "RESERVED":
            inventory_service.release_stock(item.variant, item.quantity, order_id=order.id,
                                            user_id=by_user.id if by_user else None, note="Order cancelled")
        elif order.inventory_state == "DEDUCTED":
            inventory_service.restore_stock(item.variant, item.quantity, order_id=order.id,
                                            user_id=by_user.id if by_user else None, note="Order cancelled")
    order.inventory_state = "RELEASED"
    order.order_status = OrderStatus.CANCELLED
    if order.payment_status == PaymentStatus.PAID:
        order.payment_status = PaymentStatus.REFUNDED
    db.session.add(OrderEvent(order_id=order.id, status=OrderStatus.CANCELLED,
                              note=reason or "Cancelled by customer", user_id=by_user.id if by_user else None))
    db.session.commit()
    log_action("ORDER_CANCELLED", "Order", order.order_number, reason)
    return order


def update_order_status(order, new_status, note=None, by_user=None):
    if new_status not in OrderStatus.ALL:
        raise CheckoutError("Invalid order status.")
    order.order_status = new_status
    order.tracking_note = note
    order.updated_at = utcnow()
    db.session.add(OrderEvent(order_id=order.id, status=new_status, note=note, user_id=by_user.id if by_user else None))
    if new_status == OrderStatus.DELIVERED and order.payment_method == PaymentMethod.COD:
        order.payment_status = PaymentStatus.PAID
    db.session.commit()
    log_action("ORDER_STATUS_UPDATED", "Order", order.order_number, f"-> {new_status}")
    from .notification_service import notify
    notify(order.user_id, f"Order {OrderStatus.label(new_status)}",
          f"Your order {order.order_number} is now {OrderStatus.label(new_status)}.",
          "ORDER", f"/customer/orders/{order.order_number}")
    return order
