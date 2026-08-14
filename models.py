from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Trade(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    symbol: str
    timeframe: str
    direction: str  # BUY or SELL
    entry_price: float
    sl_price: float
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    score: Optional[float] = None
    grade: Optional[str] = None
    status: str = "OPEN"  # OPEN, TP1, TP2, TP3, SL
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    telegram_msg_id: Optional[int] = None
    r_multiple: Optional[float] = None
