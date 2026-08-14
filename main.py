import asyncio
import logging

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from sqlmodel import Session, select, SQLModel

from config import settings
from db import engine
from models import Trade

from bot import (
    setup_bot,
    start_bot_polling,
    send_telegram_message,
    edit_telegram_message,
)

from utils import (
    format_open_signal,
    format_closed_signal,
    calculate_r_multiple,
    safe_float,
)


logging.basicConfig(level=logging.INFO)


# Create database tables.
SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Starts the Telegram bot when FastAPI starts.
    """
    bot_app = setup_bot()

    await bot_app.initialize()
    await bot_app.start()

    polling_task = asyncio.create_task(start_bot_polling(bot_app))

    try:
        yield
    finally:
        polling_task.cancel()

        try:
            await polling_task
        except asyncio.CancelledError:
            pass

        await bot_app.stop()
        await bot_app.shutdown()


app = FastAPI(
    title="SMC Telegram Signal Bot",
    lifespan=lifespan,
)


class SignalPayload(BaseModel):
    symbol: str
    timeframe: str

    # BUY, SELL, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT
    signal: str

    entry: str

    stop_loss: Optional[str] = None

    tp1: Optional[str] = None
    tp2: Optional[str] = None
    tp3: Optional[str] = None

    score: Optional[str] = None
    grade: Optional[str] = None


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """
    TradingView may send non-JSON text alerts.

    Instead of returning 422 and making TradingView think the webhook failed,
    we return 200 and ignore the payload.
    """
    logging.warning("Ignoring invalid webhook payload: %s", exc)

    return JSONResponse(
        status_code=200,
        content={"status": "ignored"},
    )


@app.get("/")
async def health():
    return {
        "status": "ok",
    }


def first_valid(*values):
    """
    Returns the first value that is not None.
    """
    for value in values:
        if value is not None:
            return value

    return None


def find_open_trade(session: Session, payload: SignalPayload) -> Optional[Trade]:
    """
    Finds the correct open trade for a TP/SL alert.

    Matches by:
    - symbol
    - timeframe
    - status OPEN

    If multiple trades match, tries to match entry price with tolerance.
    """
    statement = select(Trade).where(
        Trade.symbol == payload.symbol,
        Trade.timeframe == payload.timeframe,
        Trade.status == "OPEN",
    )

    trades = session.exec(statement).all()

    if not trades:
        return None

    if len(trades) == 1:
        return trades[0]

    payload_entry = safe_float(payload.entry)

    if payload_entry is None:
        return trades[0]

    for trade in trades:
        tolerance = max(1e-8, abs(trade.entry_price) * 1e-6)

        if abs(trade.entry_price - payload_entry) <= tolerance:
            return trade

    return trades[0]


async def process_signal(payload: SignalPayload) -> None:
    """
    Processes TradingView webhook signals.
    """
    try:
        with Session(engine) as session:

            # ----------------------------------------------------------
            # NEW SIGNAL
            # ----------------------------------------------------------
            if payload.signal in ["BUY", "SELL"]:

                existing_trade = session.exec(
                    select(Trade).where(
                        Trade.symbol == payload.symbol,
                        Trade.timeframe == payload.timeframe,
                        Trade.status == "OPEN",
                    )
                ).first()

                if existing_trade:
                    logging.info(
                        "Ignoring duplicate open signal for %s %s",
                        payload.symbol,
                        payload.timeframe,
                    )
                    return

                entry_price = safe_float(payload.entry)
                sl_price = safe_float(payload.stop_loss)

                if entry_price is None:
                    logging.error("Invalid entry price in webhook payload")
                    return

                if sl_price is None:
                    logging.error("Invalid stop loss in webhook payload")
                    return

                trade = Trade(
                    symbol=payload.symbol,
                    timeframe=payload.timeframe,
                    direction=payload.signal,
                    entry_price=entry_price,
                    sl_price=sl_price,
                    tp1_price=safe_float(payload.tp1),
                    tp2_price=safe_float(payload.tp2),
                    tp3_price=safe_float(payload.tp3),
                    score=safe_float(payload.score),
                    grade=payload.grade,
                )

                # Save trade first.
                session.add(trade)
                session.commit()
                session.refresh(trade)

                # Then try to send Telegram message.
                try:
                    message_id = await send_telegram_message(
                        format_open_signal(payload.model_dump())
                    )

                    trade.telegram_msg_id = message_id
                    session.add(trade)
                    session.commit()

                except Exception:
                    logging.exception("Failed to send Telegram open signal message")

                return

            # ----------------------------------------------------------
            # TRADE CLOSE SIGNAL
            # ----------------------------------------------------------
            if payload.signal.endswith("_HIT"):

                trade = find_open_trade(session, payload)

                if trade is None:
                    logging.warning(
                        "No open trade found for %s %s",
                        payload.symbol,
                        payload.timeframe,
                    )
                    return

                new_status = payload.signal.replace("_HIT", "")

                exit_price = None

                if new_status == "TP1":
                    exit_price = trade.tp1_price

                elif new_status == "TP2":
                    exit_price = first_valid(
                        trade.tp2_price,
                        trade.tp1_price,
                    )

                elif new_status == "TP3":
                    exit_price = first_valid(
                        trade.tp3_price,
                        trade.tp2_price,
                        trade.tp1_price,
                    )

                elif new_status == "SL":
                    exit_price = trade.sl_price

                # Final fallback.
                if exit_price is None:
                    exit_price = safe_float(payload.entry)

                if exit_price is None:
                    logging.error("No valid exit price available for trade close")
                    return

                trade.status = new_status
                trade.closed_at = datetime.now(timezone.utc)

                trade.r_multiple = calculate_r_multiple(
                    trade.direction,
                    trade.entry_price,
                    exit_price,
                    trade.sl_price,
                )

                session.add(trade)
                session.commit()
                session.refresh(trade)

                if trade.telegram_msg_id:
                    try:
                        await edit_telegram_message(
                            trade.telegram_msg_id,
                            format_closed_signal(
                                trade,
                                trade.status,
                                exit_price,
                            ),
                        )
                    except Exception:
                        logging.exception("Failed to edit Telegram closed signal message")

                return

            logging.warning("Unhandled signal type: %s", payload.signal)

    except Exception:
        logging.exception("Failed to process webhook payload")


@app.post("/webhook")
async def webhook(
    payload: SignalPayload,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    TradingView webhook endpoint.
    """
    secret = request.headers.get("X-Webhook-Secret") or request.query_params.get("secret")

    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Invalid secret",
        )

    background_tasks.add_task(process_signal, payload)

    return {
        "status": "success",
    }
