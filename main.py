import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select
from datetime import datetime
import logging

from config import settings
from models import Trade
from bot import setup_bot, start_bot_polling, send_telegram_message, edit_telegram_message
from utils import format_open_signal, format_closed_signal, calculate_r_multiple

# Database engine from centralized module
from db import engine

# Ensure tables exist (after models are imported)
from sqlmodel import SQLModel
SQLModel.metadata.create_all(engine)

# Lifespan (Starts Telegram Bot alongside FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = setup_bot()
    task = asyncio.create_task(start_bot_polling(bot_app))
    yield
    task.cancel()
    await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

class SignalPayload(BaseModel):
    symbol: str
    timeframe: str
    signal: str  # BUY, SELL, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT
    entry: str
    stop_loss: Optional[str] = None
    tp1: Optional[str] = None
    tp2: Optional[str] = None
    tp3: Optional[str] = None
    score: Optional[str] = None
    grade: Optional[str] = None

async def process_signal(payload: SignalPayload):
    with Session(engine) as session:
        if payload.signal in ["BUY", "SELL"]:
            # Check for duplicate open trade for same symbol
            exists = session.exec(
                select(Trade).where(Trade.symbol == payload.symbol, Trade.status == "OPEN")
            ).first()
            if exists:
                return

            # Safely coerce optional fields
            try:
                entry_price = float(payload.entry)
            except (TypeError, ValueError):
                logging.error("Invalid entry price in payload")
                return

            try:
                sl_price = float(payload.stop_loss) if payload.stop_loss else 0.0
            except (TypeError, ValueError):
                logging.error("Invalid stop loss in payload")
                return

            trade = Trade(
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                direction=payload.signal,
                entry_price=entry_price,
                sl_price=sl_price,
                tp1_price=float(payload.tp1) if payload.tp1 else None,
                tp2_price=float(payload.tp2) if payload.tp2 else None,
                tp3_price=float(payload.tp3) if payload.tp3 else None,
                score=float(payload.score) if payload.score else None,
                grade=payload.grade
            )
            msg_id = await send_telegram_message(format_open_signal(payload.model_dump()))
            trade.telegram_msg_id = msg_id
            session.add(trade)
            session.commit()
            session.refresh(trade)

        elif payload.signal.endswith("_HIT"):
            # Find the first OPEN trade for this symbol (matching entry by float equality is fragile;
            # prefer symbol+OPEN. If you need exact entry matching, send an identifier or telegram_msg_id.)
            trade = session.exec(
                select(Trade).where(Trade.symbol == payload.symbol, Trade.status == "OPEN")
            ).first()

            if not trade:
                logging.warning("No open trade found for symbol %s", payload.symbol)
                return

            # Determine which exit price to use based on the signal
            exit_price = None
            new_status = payload.signal.replace("_HIT", "")  # TP1, TP2, TP3, SL

            if new_status == "TP1":
                exit_price = trade.tp1_price
            elif new_status == "TP2":
                exit_price = trade.tp2_price or trade.tp1_price
            elif new_status == "TP3":
                exit_price = trade.tp3_price or trade.tp2_price or trade.tp1_price
            elif new_status == "SL":
                exit_price = trade.sl_price

            # Fall back to payload.entry if no TP/SL was available
            if exit_price is None:
                try:
                    exit_price = float(payload.entry)
                except (TypeError, ValueError):
                    logging.error("No valid exit price available for trade close")
                    return

            trade.status = new_status
            trade.closed_at = datetime.utcnow()
            trade.r_multiple = calculate_r_multiple(trade.direction, trade.entry_price, float(exit_price), trade.sl_price)
            session.add(trade)
            session.commit()
            session.refresh(trade)

            if trade.telegram_msg_id:
                await edit_telegram_message(trade.telegram_msg_id, format_closed_signal(trade, trade.status, float(exit_price)))

@app.post("/webhook")
async def webhook(payload: SignalPayload, request: Request, background_tasks: BackgroundTasks):
    # Security Check
    secret = request.headers.get("X-Webhook-Secret") or request.query_params.get("secret")
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")
        
    background_tasks.add_task(process_signal, payload)
    return {"status": "success"}
