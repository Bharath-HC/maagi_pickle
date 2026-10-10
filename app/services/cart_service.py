from ..extensions import db
from ..models import Cart, CartItem, ProductVariant
from . import pricing_service


class CartError(Exception):
    pass


def get_or_create_cart(user):
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.commit()
    return cart


def _variant_or_404(variant_id):
    variant = db.session.get(ProductVariant, variant_id)
    if not variant or not variant.active or not variant.product.active:
        raise CartError("This product is not available right now.")
    return variant


def add_item(user, variant_id, quantity=1):
    cart = get_or_create_cart(user)
    variant = _variant_or_404(variant_id)
    moq = pricing_service.moq_for(variant.product, user.role)
    existing = next((i for i in cart.items if i.variant_id == variant.id), None)
    new_qty = (existing.quantity if existing else 0) + max(1, int(quantity))
    if new_qty < moq:
        new_qty = moq
    if new_qty > variant.available_stock:
        raise CartError(f"Only {variant.available_stock} unit(s) of {variant.product.name} ({variant.label}) in stock.")
    if existing:
        existing.quantity = new_qty
    else:
        cart.items.append(CartItem(variant_id=variant.id, quantity=new_qty))
    db.session.commit()
    return cart


def update_item(user, item_id, quantity):
    cart = get_or_create_cart(user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise CartError("Item not found in your cart.")
    quantity = int(quantity)
    moq = pricing_service.moq_for(item.variant.product, user.role)
    if quantity <= 0:
        cart.items.remove(item)
        db.session.delete(item)
    else:
        if quantity < moq:
            raise CartError(f"Minimum order quantity for this product is {moq}.")
        if quantity > item.variant.available_stock:
            raise CartError(f"Only {item.variant.available_stock} unit(s) available.")
        item.quantity = quantity
    db.session.commit()
    return cart


def remove_item(user, item_id):
    cart = get_or_create_cart(user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item:
        db.session.delete(item)
        db.session.commit()
    return cart


def clear_cart(cart):
    for item in list(cart.items):
        db.session.delete(item)
    cart.coupon_code = None
    db.session.commit()


def cart_lines(cart, role):
    lines = []
    for item in cart.items:
        variant = item.variant
        unit_price = pricing_service.variant_price(variant, role)
        lines.append({
            "item": item,
            "variant": variant,
            "product": variant.product,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "line_total": unit_price * item.quantity,
            "stock_ok": item.quantity <= variant.available_stock,
        })
    return lines


def cart_subtotal(cart, role):
    return sum((line["line_total"] for line in cart_lines(cart, role)), start=pricing_service.D(0))
