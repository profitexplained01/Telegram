def calculate_r_multiple(direction: str, entry: float, exit_price: float, sl: float) -> float:
    """Calculates R-Multiple (Reward / Risk)."""
    try:
        entry, exit_price, sl = float(entry), float(exit_price), float(sl)
    except (TypeError, ValueError):
        return 0.0

    risk = abs(entry - sl)
    if risk == 0:
        return 0.0
    if direction == "BUY":
        reward = exit_price - entry
    else:
        reward = entry - exit_price
    return reward / risk

def format_open_signal(data: dict) -> str:
    symbol = data.get("symbol", "UNKNOWN")
    timeframe = data.get("timeframe", "?")
    grade = data.get("grade") or "N/A"
    score = data.get("score") or "N/A"
    entry = data.get("entry", "?")
    stop_loss = data.get("stop_loss", "?")
    tp1 = data.get("tp1", "-")
    tp2 = data.get("tp2", "-")
    tp3 = data.get("tp3", "-")
    signal = data.get("signal", "SIGNAL")

    return (
        f"🚀 *NEW {signal} SIGNAL* | {symbol} ({timeframe}m)\n"
        f"🎯 *Grade:* {grade} (Score: {score})\n\n"
        f"💰 *Entry:* `{entry}`\n"
        f"🛑 *Stop Loss:* `{stop_loss}`\n"
        f"✅ *TP1:* `{tp1}`\n"
        f"✅ *TP2:* `{tp2}`\n"
        f"✅ *TP3:* `{tp3}`\n\n"
        f"_Powered by SMC Fusion v2.4_"
    )

def format_closed_signal(trade, exit_status: str, exit_price: float) -> str:
    r = calculate_r_multiple(trade.direction, trade.entry_price, exit_price, trade.sl_price)
    emoji = "🟢" if (exit_status or "").startswith("TP") else "🔴"
    grade = trade.grade or "N/A"
    return (
        f"{emoji} *TRADE CLOSED: {exit_status}* | {trade.symbol}\n"
        f"🎯 *Grade:* {grade}\n\n"
        f"💰 *Entry:* `{trade.entry_price}`\n"
        f"🏁 *Exit:* `{exit_price}`\n"
        f"📉 *PnL:* `{r:.2f}R`\n"
    )
