import os
import re
import secrets
import unicodedata
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def unique_slug(model, base_text, db_session, instance_id=None):
    base = slugify(base_text) or "item"
    slug = base
    i = 1
    query = model.query.filter_by(slug=slug)
    while query.filter(model.id != instance_id).first() if instance_id else query.first():
        i += 1
        slug = f"{base}-{i}"
        query = model.query.filter_by(slug=slug)
    return slug


def order_number():
    return f"MAAGI-{datetime.utcnow().strftime('%Y')}-{secrets.randbelow(900000) + 100000}"


def invoice_number():
    return f"INV-{datetime.utcnow().strftime('%Y%m')}-{secrets.randbelow(90000) + 10000}"


def bulk_reference():
    return f"BULK-{secrets.randbelow(900000) + 100000}"


def allowed_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_upload(file_storage, subfolder="products"):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_image(file_storage.filename):
        raise ValueError("Only JPG, JPEG, PNG and WEBP images are allowed.")
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{secrets.token_hex(8)}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, unique_name)
    file_storage.save(dest)
    return f"uploads/{subfolder}/{unique_name}"


def rupees(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    return f"₹{value:,.2f}".replace(".00", "") if value == int(value) else f"₹{value:,.2f}"


def client_ip(request):
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() if fwd else request.remote_addr
