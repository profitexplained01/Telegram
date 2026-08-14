from html import escape
from typing import Any, Optional


def clean(value: Any, default: str = "N/A") -> str:
    """
    Safely convert a value into a display string.
    Handles None, empty strings, and whitespace-only strings.
    """
    if value is None:
        return default

    text = str(value).strip()

    if text == "":
        return default

    return text


def safe_float(value: Any) -> Optional[float]:
    """
    Safely convert a value to float.
    Returns None if invalid.
    """
    if value is None:
        return None

    text = str(value).strip()

    if text == "" or text.lower() == "n/a":
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def calculate_r_multiple(direction: str, entry: Any, exit_price: Any, sl: Any) -> float:
    """
    Calculates R-Multiple.

    R = Reward / Risk

    BUY:
        reward = exit - entry
        risk = entry - stop_loss

    SELL:
        reward = entry - exit
        risk = stop_loss - entry
    """
    entry_f = safe_float(entry)
    exit_f = safe_float(exit_price)
    sl_f = safe_float(sl)

    if entry_f is None or exit_f is None or sl_f is None:
        return 0.0

    risk = abs(entry_f - sl_f)

    if risk == 0:
        return 0.0

    d = clean(direction, "").upper()

    if d == "BUY":
        reward = exit_f - entry_f
    elif d == "SELL":
        reward = entry_f - exit_f
    else:
        return 0.0

    return reward / risk


def format_timeframe(timeframe: Any) -> str:
    """
    Converts TradingView timeframe codes into readable labels.

    Examples:
        15  -> 15m
        60  -> 1h
        240 -> 4h
        1D  -> 1D
    """
    tf = clean(timeframe, "?")

    mapping = {
        "1": "1m",
        "3": "3m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "45": "45m",
        "60": "1h",
        "120": "2h",
        "240": "4h",
        "360": "6h",
        "720": "12h",
        "1D": "1D",
        "3D": "3D",
        "1W": "1W",
        "1M": "1M",
    }

    return mapping.get(tf, tf)


def format_open_signal(data: dict) -> str:
    """
    Formats a new BUY/SELL signal for Telegram using HTML.
    """
    signal = escape(clean(data.get("signal"), "SIGNAL"))
    symbol = escape(clean(data.get("symbol"), "UNKNOWN"))
    timeframe = escape(format_timeframe(data.get("timeframe")))
    grade = escape(clean(data.get("grade"), "N/A"))
    score = escape(clean(data.get("score"), "N/A"))

    entry = escape(clean(data.get("entry"), "?"))
    stop_loss = escape(clean(data.get("stop_loss"), "?"))

    tp1 = escape(clean(data.get("tp1"), "-"))
    tp2 = escape(clean(data.get("tp2"), "-"))
    tp3 = escape(clean(data.get("tp3"), "-"))

    return (
        f"🚀 <b>NEW {signal} SIGNAL</b> | {symbol} ({timeframe})\n"
        f"🎯 <b>Grade:</b> {grade} (Score: {score})\n\n"
        f"💰 <b>Entry:</b> <code>{entry}</code>\n"
        f"🛑 <b>Stop Loss:</b> <code>{stop_loss}</code>\n"
        f"✅ <b>TP1:</b> <code>{tp1}</code>\n"
        f"✅ <b>TP2:</b> <code>{tp2}</code>\n"
        f"✅ <b>TP3:</b> <code>{tp3}</code>\n\n"
        f"<i>Powered by SMC Fusion v2.4</i>"
    )


def format_closed_signal(trade: Any, exit_status: str, exit_price: Any) -> str:
    """
    Formats a closed trade message for Telegram using HTML.
    """
    status = clean(exit_status, "CLOSED")
    emoji = "🟢" if status.upper().startswith("TP") else "🔴"

    r = calculate_r_multiple(
        getattr(trade, "direction", None),
        getattr(trade, "entry_price", None),
        exit_price,
        getattr(trade, "sl_price", None),
    )

    symbol = escape(clean(getattr(trade, "symbol", None), "UNKNOWN"))
    timeframe = escape(format_timeframe(getattr(trade, "timeframe", None)))
    grade = escape(clean(getattr(trade, "grade", None), "N/A"))

    entry = escape(clean(getattr(trade, "entry_price", None), "?"))
    exit_text = escape(clean(exit_price, "?"))

    return (
        f"{emoji} <b>TRADE CLOSED: {status}</b> | {symbol} ({timeframe})\n"
        f"🎯 <b>Grade:</b> {grade}\n\n"
        f"💰 <b>Entry:</b> <code>{entry}</code>\n"
        f"🏁 <b>Exit:</b> <code>{exit_text}</code>\n"
        f"📉 <b>PnL:</b> <code>{r:.2f}R</code>\n"
    )
