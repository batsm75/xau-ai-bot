"""Pengambilan data market: TwelveData (utama) + SoSoValue (kripto, opsional).

Kedua sumber diambil paralel. Jika satu sumber gagal, sumber lain tetap dipakai.
Hasil dirangkum menjadi ringkasan OHLC + level penting untuk dikirim ke AI.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests

from config.settings import Settings

TIMEOUT = 20
MAX_CANDLES = 80  # jumlah candle terakhir yang dikirim ke AI (hemat token)


def _ringkas_ohlc(candles: list[dict]) -> dict:
    """Hitung level statistik sederhana dari daftar candle {o,h,l,c}."""
    if not candles:
        return {}
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    return {
        "highest": max(highs),
        "lowest": min(lows),
        "current": closes[-1],
        "open_pertama": float(candles[0]["open"]),
        "jumlah_candle": len(candles),
        "rata_close": round(sum(closes) / len(closes), 6),
    }


def fetch_twelvedata(symbol: str, interval: str) -> Optional[dict]:
    """Time series + quote dari TwelveData. Return None jika gagal/tanpa key."""
    if not Settings.TWELVEDATA_API_KEY:
        return None
    base = Settings.TWELVEDATA_BASE_URL.rstrip("/")
    try:
        ts = requests.get(
            f"{base}/time_series",
            params={
                "symbol": symbol,
                "interval": interval,
                "outputsize": MAX_CANDLES,
                "apikey": Settings.TWELVEDATA_API_KEY,
            },
            timeout=TIMEOUT,
        ).json()
        if "values" not in ts:
            return {"sumber": "TwelveData", "error": ts.get("message", str(ts)[:200])}

        candles = []
        for row in ts["values"][:MAX_CANDLES]:
            candles.append({
                "datetime": row.get("datetime", ""),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": row.get("volume", ""),
            })
        candles.reverse()  # urut kronologis (lama -> baru)

        quote = {}
        try:
            q = requests.get(
                f"{base}/quote",
                params={"symbol": symbol, "apikey": Settings.TWELVEDATA_API_KEY},
                timeout=TIMEOUT,
            ).json()
            if "close" in q:
                quote = {"harga": q.get("close"), "change_pct": q.get("percent_change")}
        except Exception:
            pass

        return {
            "sumber": "TwelveData",
            "candles": candles,
            "ringkasan": _ringkas_ohlc(candles),
            "quote": quote,
        }
    except Exception as e:
        return {"sumber": "TwelveData", "error": str(e)[:200]}


def fetch_sosovalue(symbol: str, interval: str) -> Optional[dict]:
    """Historical klines dari SoSoValue (khusus kripto). Endpoint path configurable.

    Karena path persisnya bisa berubah mengikuti versi API, kita coba beberapa pola
    umum dan pakai yang pertama berhasil. Return None jika semua gagal / tanpa key.
    """
    if not Settings.SOSOVALUE_API_KEY:
        return None
    base = Settings.SOSOVALUE_BASE_URL.rstrip("/")
    headers = {"Accept": "application/json", "x-soso-api-key": Settings.SOSOVALUE_API_KEY}
    kandidat_path = [
        Settings.SOSOVALUE_KLINE_PATH,
        "/currency/klines",
        "/market/klines",
        "/klines",
    ]
    params_candidates = [
        {"symbol": symbol, "interval": interval, "limit": MAX_CANDLES},
        {"currency_id": symbol, "interval": interval, "limit": MAX_CANDLES},
        {"pair": symbol, "interval": interval, "limit": MAX_CANDLES},
    ]
    for path in kandidat_path:
        for params in params_candidates:
            try:
                r = requests.get(f"{base}{path}", headers=headers, params=params, timeout=TIMEOUT)
                if r.status_code != 200:
                    continue
                data = r.json()
                # Coba ekstrak list candle dari berbagai kemungkinan key
                rows = None
                for k in ("data", "klines", "candles", "result", "list"):
                    if isinstance(data, dict) and isinstance(data.get(k), list):
                        rows = data[k]
                        break
                if isinstance(data, list):
                    rows = data
                if not rows:
                    continue

                candles = []
                for row in rows[:MAX_CANDLES]:
                    if isinstance(row, dict):
                        o = row.get("open") or row.get("o")
                        h = row.get("high") or row.get("h")
                        l = row.get("low") or row.get("l")
                        c = row.get("close") or row.get("c")
                        if None in (o, h, l, c):
                            continue
                        candles.append({"open": float(o), "high": float(h),
                                        "low": float(l), "close": float(c)})
                    elif isinstance(row, (list, tuple)) and len(row) >= 5:
                        # format [ts, o, h, l, c, vol]
                        candles.append({"open": float(row[1]), "high": float(row[2]),
                                        "low": float(row[3]), "close": float(row[4])})
                if candles:
                    if candles[0]["open"] > 0 and len(candles) > 1:
                        pass
                    return {
                        "sumber": f"SoSoValue ({path})",
                        "candles": candles,
                        "ringkasan": _ringkas_ohlc(candles),
                    }
            except Exception:
                continue
    return {"sumber": "SoSoValue", "error": "tidak ada endpoint kline yang cocok (cek SOSOVALUE_KLINE_PATH di .env)"}


def ambil_data_market(symbol: str, interval: str) -> dict:
    """Ambil dari kedua sumber paralel, gabungkan hasilnya."""
    hasil: dict = {"symbol": symbol, "interval": interval, "sumber_berhasil": [], "error": []}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {
            ex.submit(fetch_twelvedata, symbol, interval): "TwelveData",
            ex.submit(fetch_sosovalue, symbol, interval): "SoSoValue",
        }
        for fut in as_completed(futs):
            nama = futs[fut]
            try:
                data = fut.result()
            except Exception as e:
                hasil["error"].append(f"{nama}: {str(e)[:150]}")
                continue
            if data is None:
                continue
            if "error" in data:
                hasil["error"].append(f"{nama}: {data['error']}")
            else:
                hasil["sumber_berhasil"].append(data["sumber"])
                hasil.setdefault("candles", []).extend(data.get("candles", []))
                if "ringkasan" in data:
                    hasil["ringkasan"] = data["ringkasan"]
                if data.get("quote"):
                    hasil["quote"] = data["quote"]

    if hasil.get("candles"):
        hasil["candles"] = sorted(hasil["candles"], key=lambda c: c.get("datetime", ""))[-MAX_CANDLES:]
        if "ringkasan" not in hasil:
            hasil["ringkasan"] = _ringkas_ohlc(hasil["candles"])
    return hasil


def format_untuk_ai(data: dict) -> str:
    """Ubah data market menjadi teks ringkas yang siap dikirim ke AI."""
    lines = [
        f"INSTRUMEN: {data.get('symbol')} | TIMEFRAME: {data.get('interval')}",
        f"SUMBER DATA: {', '.join(data.get('sumber_berhasil', ['-'])) or 'TIDAK ADA'}",
    ]
    if data.get("quote"):
        q = data["quote"]
        lines.append(f"HARGA TERKINI: {q.get('harga')} (change {q.get('change_pct')}%)")
    if data.get("ringkasan"):
        r = data["ringkasan"]
        lines.append(
            f"RINGKASAN {r.get('jumlah_candle')} candle: "
            f"open={r.get('open_pertama')}, high={r.get('highest')}, "
            f"low={r.get('lowest')}, close_now={r.get('current')}, avg_close={r.get('rata_close')}"
        )
    if data.get("error"):
        lines.append("CATATAN SUMBER DATA: " + " | ".join(data["error"]))

    lines.append("\nOHLC (terbaru di akhir, format O/H/L/C):")
    for c in data.get("candles", [])[-60:]:
        dt = c.get("datetime", "")
        lines.append(f"  {dt} {c['open']} {c['high']} {c['low']} {c['close']}")
    return "\n".join(lines)
