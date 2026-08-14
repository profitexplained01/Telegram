# Telegram SMC Signals

A small FastAPI + Telegram bot service to receive SMC signals via webhook and post/edit messages in a Telegram channel. Uses SQLModel (SQLite by default) to persist trades and compute simple performance stats.

Features
- Webhook endpoint for incoming signals
- Posts new trade signals to Telegram
- Edits the Telegram message when a TP/SL is hit
- Tracks trades and computes simple stats via /stats command

Quickstart
1. Copy `.env.example` to `.env` and fill in your values.
2. Build & run with Docker (or run locally with Python 3.11):

   docker build -t telegram-smc .
   docker run -e PORT=8000 -p 8000:8000 \
     --env-file .env telegram-smc

3. Send POST requests to `/webhook` with header `X-Webhook-Secret` or query param `?secret=` matching your WEBHOOK_SECRET.

Security
- Keep WEBHOOK_SECRET secret. Use HTTPS in production.

Notes
- For reliable matching of closing signals consider including the trade ID or telegram_msg_id in future webhook payloads. Current logic matches by symbol and OPEN status.
