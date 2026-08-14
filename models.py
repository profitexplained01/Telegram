import uuid

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Trade(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    symbol: str = Field(index=True)
    timeframe: str = Field(index=True)

    # BUY or SELL
    direction: str

    entry_price: float
    sl_price: float

    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None

    score: Optional[float] = None
    grade: Optional[str] = None

    # OPEN, TP1, TP2, TP3, SL
    status: str = Field(default="OPEN", index=True)

    opened_at: datetime = Field(default_factory=utcnow)
    closed_at: Optional[datetime] = None

    telegram_msg_id: Optional[int] = Field(default=None, index=True)

    # R-multiple:
    # +1.0 means you made 1R
    # -1.0 means you lost 1R
    r_multiple: Optional[float] = None
