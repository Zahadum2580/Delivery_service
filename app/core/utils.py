from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

from pydantic import NonNegativeFloat

from app.core.config import settings


def round_3(v: NonNegativeFloat) -> NonNegativeFloat:
    """Банковское округление до 3 знаков."""
    return float(Decimal(str(v)).quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN))


def round_2(v: NonNegativeFloat) -> NonNegativeFloat:
    """Банковское округление до 2 знаков."""
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def msk_now() -> datetime:
    return datetime.now(tz=ZoneInfo(settings.TZ))
