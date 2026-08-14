import logging

from typing import Optional

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import BadRequest

from sqlmodel import Session, select

from config import settings
from models import Trade
from db import engine


logging.basicConfig(level=logging.INFO)


_application: Optional[Application] = None


def get_bot() -> Bot:
    """
    Returns the initialized Telegram bot instance.
    """
    if _application is None or _application.bot is None:
        raise RuntimeError("Telegram bot has not been initialized yet.")

    return _application.bot


async def send_telegram_message(text: str) -> int:
    """
    Sends a message to the configured Telegram channel.
    Returns the Telegram message ID so we can edit it later.
    """
    bot = get_bot()

    message = await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="HTML",
    )

    return message.message_id


async def edit_telegram_message(msg_id: int, text: str) -> None:
    """
    Edits an existing Telegram message.
    """
    try:
        bot = get_bot()

        await bot.edit_message_text(
            chat_id=settings.TELEGRAM_CHAT_ID,
            message_id=msg_id,
            text=text,
            parse_mode="HTML",
        )

    except BadRequest as exc:
        error_text = str(exc).lower()

        # This happens when the new message is identical to the old one.
        if "message is not modified" in error_text:
            return

        logging.error("Failed to edit Telegram message: %s", exc)

    except Exception:
        logging.exception("Unexpected error while editing Telegram message")


def is_allowed(update: Update) -> bool:
    """
    Simple authorization check.

    If TELEGRAM_ADMIN_USER_ID is not set, commands are public.
    If TELEGRAM_ADMIN_USER_ID is set, only that user can use commands.
    """
    admin_id = (settings.TELEGRAM_ADMIN_USER_ID or "").strip()

    if admin_id == "":
        return True

    user = update.effective_user

    if user is None:
        return False

    return str(user.id) == admin_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    if not is_allowed(update):
        await update.message.reply_text("Not authorized.")
        return

    await update.message.reply_text(
        "Bot is online and tracking SMC signals.\n\n"
        "Commands:\n"
        "/stats - Performance statistics\n"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    if not is_allowed(update):
        await update.message.reply_text("Not authorized.")
        return

    with Session(engine) as session:
        closed_trades = session.exec(
            select(Trade).where(Trade.status != "OPEN")
        ).all()

    if not closed_trades:
        await update.message.reply_text("No closed trades yet.")
        return

    total = len(closed_trades)

    wins = len(
        [
            t
            for t in closed_trades
            if (t.status or "").upper().startswith("TP")
        ]
    )

    losses = total - wins

    win_rate = (wins / total) * 100 if total > 0 else 0.0

    r_values = [
        float(t.r_multiple)
        for t in closed_trades
        if isinstance(t.r_multiple, (int, float))
    ]

    if r_values:
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        avg_r = sum(r_values) / len(r_values)

        if gross_loss > 0:
            profit_factor_text = f"{gross_profit / gross_loss:.2f}"
        else:
            profit_factor_text = "∞"
    else:
        avg_r = 0.0
        profit_factor_text = "N/A"

    text = (
        "📊 <b>SMC Performance Stats</b>\n\n"
        f"Total Trades: {total}\n"
        f"Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)\n"
        f"Average R-Multiple: {avg_r:.2f}R\n"
        f"Profit Factor: {profit_factor_text}\n"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


def setup_bot() -> Application:
    """
    Creates the Telegram Application and registers command handlers.
    """
    global _application

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    _application = app

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    return app


async def start_bot_polling(app: Application) -> None:
    """
    Starts Telegram polling.
    """
    if app.updater is None:
        raise RuntimeError("Telegram updater is not available.")

    await app.updater.start_polling(
        drop_pending_updates=True,
    )
