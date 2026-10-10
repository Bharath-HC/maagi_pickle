import hmac
import hashlib
import secrets

from flask import current_app

from ..extensions import db
from ..models import D, Payment, PaymentStatus
from .audit_service import log_action


class PaymentError(Exception):
    pass


def razorpay_client():
    key_id = current_app.config.get("RAZORPAY_KEY_ID")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        return None
    try:
        import razorpay
    except ImportError:
        return None
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(order):
    client = razorpay_client()
    amount_paise = int(D(order.total_amount) * 100)

    if client:
        rp_order = client.order.create({
            "amount": amount_paise, "currency": "INR", "receipt": order.order_number,
            "notes": {"order_number": order.order_number},
        })
        payment = Payment(order_id=order.id, razorpay_order_id=rp_order["id"], amount=order.total_amount,
                          status="CREATED", payment_method="RAZORPAY", is_simulated=False)
        db.session.add(payment)
        db.session.commit()
        return {"mode": "razorpay", "key_id": current_app.config["RAZORPAY_KEY_ID"],
                "razorpay_order_id": rp_order["id"], "amount": amount_paise, "currency": "INR"}

    if not current_app.config.get("ALLOW_PAYMENT_SIMULATION"):
        raise PaymentError("Online payment is not configured yet. Please choose Cash on Delivery or contact us.")

    sim_order_id = f"order_SIM{secrets.token_hex(8)}"
    payment = Payment(order_id=order.id, razorpay_order_id=sim_order_id, amount=order.total_amount,
                      status="CREATED", payment_method="RAZORPAY", is_simulated=True)
    db.session.add(payment)
    db.session.commit()
    return {"mode": "simulation", "razorpay_order_id": sim_order_id, "amount": amount_paise, "currency": "INR"}


def simulate_successful_payment_id():
    return f"pay_SIM{secrets.token_hex(8)}"


def verify_and_confirm(order, razorpay_order_id, razorpay_payment_id, razorpay_signature=None):
    payment = Payment.query.filter_by(order_id=order.id, razorpay_order_id=razorpay_order_id).first()
    if not payment:
        raise PaymentError("Payment record not found for this order.")

    if payment.status == "PAID":
        return payment  # idempotent: duplicate callback

    if payment.is_simulated:
        if not razorpay_payment_id.startswith("pay_SIM"):
            raise PaymentError("Invalid simulated payment id.")
    else:
        secret = current_app.config["RAZORPAY_KEY_SECRET"]
        payload = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        if not razorpay_signature or not hmac.compare_digest(expected, razorpay_signature):
            payment.status = "FAILED"
            payment.error_description = "Signature verification failed"
            db.session.commit()
            raise PaymentError("Payment verification failed. If an amount was deducted, it will be refunded automatically.")

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = "PAID"
    db.session.commit()

    from .order_service import confirm_order_payment
    confirm_order_payment(order, mark_paid=True)
    log_action("PAYMENT_VERIFIED", "Payment", str(payment.id), order.order_number)
    return payment


def mark_payment_failed(order, razorpay_order_id, description="Payment failed"):
    payment = Payment.query.filter_by(order_id=order.id, razorpay_order_id=razorpay_order_id).first()
    if payment:
        payment.status = "FAILED"
        payment.error_description = description
        db.session.commit()
    order.payment_status = PaymentStatus.FAILED
    db.session.commit()
    return payment
