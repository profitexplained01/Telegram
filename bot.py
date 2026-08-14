import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from config import settings
from sqlmodel import Session, select
from models import Trade
from db import engine

# Initialize Bot for sending messages outside of handlers
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_telegram_message(text: str) -> int:
    msg = await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
    return msg.message_id

async def edit_telegram_message(msg_id: int, text: str):
    try:
        await bot.edit_message_text(chat_id=settings.TELEGRAM_CHAT_ID, message_id=msg_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Failed to edit message: {e}")

# --- COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is online and tracking SMC signals! Use /stats to see performance.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with Session(engine) as session:
        closed_trades = session.exec(select(Trade).where(Trade.status != "OPEN")).all()
        
        if not closed_trades:
            await update.message.reply_text("No closed trades yet.")
            return

        total = len(closed_trades)
        wins = len([t for t in closed_trades if t.status and t.status.startswith("TP")])
        losses = total - wins
        win_rate = (wins / total) * 100 if total > 0 else 0.0

        # Only include numeric r_multiple values
        r_values = [t.r_multiple for t in closed_trades if isinstance(t.r_multiple, (int, float))]

        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_r = (sum(r_values) / len(r_values)) if r_values else 0.0

        text = (
            f"📊 *SMC Performance Stats*\n"
            f"Total Trades: {total}\n"
            f"Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)\n"
            f"Average R-Multiple: {avg_r:.2f}R\n"
            f"Profit Factor: {profit_factor:.2f}\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

def setup_bot():
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    return app

async def start_bot_polling(app: Application):
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
