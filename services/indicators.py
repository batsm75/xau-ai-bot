"""Indikator teknikal murni Python (tanpa TA-Lib) — aman di Termux.

Input candles: list[dict] dengan key 'open','high','low','close' (float),
urut kronologis (lama -> baru).
"""
from __future__ import annotations


def _ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(values[:period]) / period]
    for v in values[period:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def ema(closes: list[float], period: int) -> float | None:
    s = _ema_series(closes, period)
    return round(s[-1], 5) if s else None


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0))
        losses.append(max(-ch, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    ef = _ema_series(closes, fast)
    es = _ema_series(closes, slow)
    if not ef or not es:
        return None, None, None
    # selaraskan panjang
    n = min(len(ef), len(es))
    macd_line = [ef[-n + i] - es[-n + i] for i in range(n)]
    sig = _ema_series(macd_line, signal)
    if not sig:
        return round(macd_line[-1], 5), None, None
    hist = macd_line[-1] - sig[-1]
    return round(macd_line[-1], 5), round(sig[-1], 5), round(hist, 5)


def bollinger(closes: list[float], period: int = 20, mult: float = 2.0):
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    ma = sum(window) / period
    var = sum((x - ma) ** 2 for x in window) / period
    sd = var ** 0.5
    return round(ma - mult * sd, 5), round(ma, 5), round(ma + mult * sd, 5)


def atr(candles: list[dict], period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return round(sum(trs[-period:]) / period, 5)


def _sinyal_rsi(val: float | None) -> str:
    if val is None:
        return "n/a"
    if val >= 70:
        return f"{val} (OVERBOUGHT)"
    if val <= 30:
        return f"{val} (OVERSOLD)"
    return f"{val} (netral)"


def _sinyal_macd(m, s, h) -> str:
    if m is None:
        return "n/a"
    arah = "BULLISH" if (h is not None and h > 0) else "BEARISH"
    return f"MACD={m} signal={s} hist={h} -> {arah}"


def hitung_indikator(candles: list[dict]) -> dict:
    """Kembalikan dict ringkasan indikator + teks siap kirim ke AI/user."""
    closes = [float(c["close"]) for c in candles]
    harga = closes[-1] if closes else None
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    r = rsi(closes, 14)
    m, s, h = macd(closes)
    bl, bm, bu = bollinger(closes, 20)
    a = atr(candles, 14)

    # Tren kasar dari EMA20 vs EMA50 vs harga
    tren = "netral"
    if harga and e20 and e50:
        if harga > e20 > e50:
            tren = "BULLISH (harga > EMA20 > EMA50)"
        elif harga < e20 < e50:
            tren = "BEARISH (harga < EMA20 < EMA50)"
        elif e20 > e50:
            tren = "agak BULLISH"
        else:
            tren = "agak BEARISH"

    posisi_bb = "n/a"
    if harga and bl and bu:
        if harga >= bu:
            posisi_bb = "di upper band (jenuh beli)"
        elif harga <= bl:
            posisi_bb = "di lower band (jenuh jual)"
        else:
            posisi_bb = "di tengah band"

    teks = (
        f"TREN (EMA20/50): {tren}\n"
        f"RSI(14): {_sinyal_rsi(r)}\n"
        f"MACD(12,26,9): {_sinyal_macd(m, s, h)}\n"
        f"Bollinger(20,2): lower={bl} mid={bm} upper={bu} | harga {posisi_bb}\n"
        f"ATR(14): {a} (volatilitas rata-rata per candle)"
    )
    return {
        "harga": harga, "ema20": e20, "ema50": e50, "rsi": r,
        "macd": m, "macd_signal": s, "macd_hist": h,
        "bb_lower": bl, "bb_mid": bm, "bb_upper": bu, "atr": a,
        "tren": tren, "teks": teks,
    }
