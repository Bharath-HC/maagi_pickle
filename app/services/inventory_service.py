from ..extensions import db
from ..models import InventoryTransaction


def _log(variant, order_id, txn_type, stock_change=0, reserved_change=0, note=None, user_id=None):
    db.session.add(InventoryTransaction(
        variant_id=variant.id, order_id=order_id, txn_type=txn_type,
        stock_change=stock_change, reserved_change=reserved_change,
        stock_after=variant.stock_quantity, note=note, user_id=user_id,
    ))


def reserve_stock(variant, quantity, order_id=None, user_id=None):
    variant.reserved_stock = (variant.reserved_stock or 0) + quantity
    _log(variant, order_id, "RESERVE", reserved_change=quantity, note="Reserved for order", user_id=user_id)
    variant.product.sync_stock()


def release_stock(variant, quantity, order_id=None, user_id=None, note="Reservation released"):
    variant.reserved_stock = max(0, (variant.reserved_stock or 0) - quantity)
    _log(variant, order_id, "RELEASE", reserved_change=-quantity, note=note, user_id=user_id)
    variant.product.sync_stock()


def deduct_stock(variant, quantity, order_id=None, user_id=None):
    variant.stock_quantity = max(0, (variant.stock_quantity or 0) - quantity)
    variant.reserved_stock = max(0, (variant.reserved_stock or 0) - quantity)
    _log(variant, order_id, "DEDUCT", stock_change=-quantity, reserved_change=-quantity,
         note="Stock deducted on confirmed order", user_id=user_id)
    variant.product.sync_stock()


def restore_stock(variant, quantity, order_id=None, user_id=None, note="Stock restored on cancellation"):
    variant.stock_quantity = (variant.stock_quantity or 0) + quantity
    _log(variant, order_id, "RESTORE", stock_change=quantity, note=note, user_id=user_id)
    variant.product.sync_stock()


def restock(variant, quantity, user_id=None, note="Manual restock"):
    variant.stock_quantity = (variant.stock_quantity or 0) + quantity
    _log(variant, None, "RESTOCK", stock_change=quantity, note=note, user_id=user_id)
    variant.product.sync_stock()
    db.session.commit()
