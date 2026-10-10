from datetime import datetime, timezone
from decimal import Decimal


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def D(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def q2(value):
    return D(value).quantize(Decimal("0.01"))
