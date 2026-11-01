#!/usr/bin/env python3
"""XAUUSD AI Analysis Telegram Bot.

Data: TwelveData (+SoSoValue) | Indikator: EMA/RSI/MACD/BB/ATR |
Berita: scraping RSS (BeautifulSoup4) | Otak: Groq (Llama 3.3 70B, gratis).

Jalankan: python bot.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import telebot
from telebot import types

from config.settings import SUBSCRIBERS_JSON, Settings
from core.trade_config import METODE_ANALISIS, muat, set_metode, set_rr
from services.ai_analyzer import AIAnalyzer, AIServiceError
from services.indicators import hitung_indikator
from services.market_data import ambil_data_market, format_untuk_ai
from services.news import ambil_berita, format_untuk_ai as format_berita

Settings.reload()
TOKEN = Settings.TELEGRAM_BOT_TOKEN
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN kosong. Isi di .env (dapatkan dari @BotFather).")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)
AI = AIAnalyzer()

SYSTEM_PROMPT = """Anda adalah analis teknikal & fundamental profesional untuk XAUUSD (emas).
Berdasarkan indikator teknikal, data OHLC, dan berita terbaru, hasilkan analisis
lengkap dalam Bahasa Indonesia yang ringkas dan terstruktur.

WAJIB ada:
1. BIAAS (Bullish/Bearish/Netral) + alasan.
2. RINGKASAN SINYAL TEKNIKAL (RSI, MACD, Bollinger, EMA, ATR).
3. POLA CHART & LEVEL PENTING (support/resistance, zona entry).
4. SETUP: Entry (E), Stop Loss (SL), Take Profit (TP). Hitung TP sesuai
   risk:reward user (jarak TP = R x jarak entry-SL searah bias).
5. CATATAN FUNDAMENTAL dari berita (bila ada).
6. INVALIDASI & MANAJEMEN RISIKO.

Jangan mengarang harga. Jika data tidak cukup, katakan jujur. Gunakan bullet/heading."""


# --------------------------------------------------------------------------- #
# Subscribers (broadcast otomatis)
# --------------------------------------------------------------------------- #
def _muat_subscribers() -> set[int]:
    try:
        return set(json.loads(Path(SUBSCRIBERS_JSON).read_text()))
    except Exception:
        return set()


def _simpan_subscribers(s: set[int]) -> None:
    Path(SUBSCRIBERS_JSON).write_text(json.dumps(sorted(s)))


SUBSCRIBERS: set[int] = _muat_subscribers()
BROADCAST_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Util
# --------------------------------------------------------------------------- #
def _diizinkan(chat_id: int) -> bool:
    allowed = Settings.allowed_user_ids()
    return (not allowed) or (chat_id in allowed)


def _kirim_panjang(chat_id: int, teks: str, reply_markup=None) -> None:
    """Kirim pesan, pecah bila > 4000 karakter (batas Telegram)."""
    for i in range(0, len(teks), 4000):
        bagian = teks[i:i + 4000]
        rm = reply_markup if i + 4000 >= len(teks) else None
        bot.send_message(chat_id, bagian, reply_markup=rm, disable_web_page_preview=True)


def _keyboard_menu_utama() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Analisa XAUUSD", callback_data="analisa"),
        types.InlineKeyboardButton("⚙️ Pengaturan", callback_data="seting"),
        types.InlineKeyboardButton("🔑 Status API", callback_data="status"),
        types.InlineKeyboardButton("🔔 Broadcast Otomatis", callback_data="submenu"),
    )
    return kb


def _keyboard_timeframe() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.add(*[types.InlineKeyboardButton(tf, callback_data=f"tf:{tf}")
             for tf in ["15min", "30min", "1h", "4h", "1day"]])
    kb.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu"))
    return kb


def _keyboard_aksi(symbol: str, tf: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{symbol}|{tf}"),
        types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu"),
    )
    return kb


# --------------------------------------------------------------------------- #
# Mesin analisis (dipakai command & broadcast)
# --------------------------------------------------------------------------- #
def lakukan_analisis(symbol: str, interval: str) -> tuple[str, types.InlineKeyboardMarkup | None]:
    cfg = muat()
    data = ambil_data_market(symbol, interval)
    if not data.get("candles") and not data.get("ringkasan"):
        return (
            "❌ Gagal ambil data market.\n"
            "Kemungkinan: API key TwelveData/SoSoValue belum diisi, simbol tidak dikenal, atau koneksi gagal.\n"
            f"Error: {' | '.join(data.get('error', ['-']))}",
            _keyboard_menu_utama(),
        )

    ind = hitung_indikator(data["candles"])
    berita = ambil_berita(5)
    data_teks = format_untuk_ai(data)
    prompt = (
        f"INSTRUMEN: {symbol} | TIMEFRAME: {interval}\n"
        f"METODE: {cfg['metode_kode']} ({cfg['metode_nama']}) | RISK:REWARD: {cfg['risk_reward']}\n\n"
        f"=== INDIKATOR TEKNIKAL ===\n{ind['teks']}\n\n"
        f"=== {format_berita(berita)} ===\n\n"
        f"=== DATA OHLC ===\n{data_teks}\n\n"
        "Lakukan analisis lengkap sesuai format yang diminta."
    )

    try:
        hasil_ai, provider = AI.analisis(prompt, SYSTEM_PROMPT)
    except AIServiceError as e:
        return (f"❌ Kedua provider AI gagal:\n{e}", _keyboard_menu_utama())

    jam = datetime.now().strftime("%Y-%m-%d %H:%M")
    laporan = (
        f"📊 ANALISA {symbol} ({interval})\n"
        f"⏰ {jam} WIB | Harga: {ind['harga']}\n"
        f"🤖 AI: {provider} | Metode: {cfg['metode_kode']} | RR: {cfg['risk_reward']}\n"
        f"📈 Sumber data: {', '.join(data.get('sumber_berhasil', ['-']))}\n"
        f"{'-' * 34}\n\n"
        f"=== INDIKATOR ===\n{ind['teks']}\n\n"
        f"=== ANALISA AI ===\n{hasil_ai}\n\n"
        f"{'-' * 34}\n"
        f"⚠️ Hanya edukasi, bukan saran investasi. Kelola risiko Anda."
    )
    return laporan, _keyboard_aksi(symbol, interval)


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
@bot.message_handler(commands=["start", "help", "menu"])
def cmd_start(m):
    if not _diizinkan(m.chat.id):
        bot.reply_to(m, "⛔ Akses ditolak. Hubungi owner bot ini.")
        return
    bot.send_message(m.chat.id,
                     "👋 Selamat datang di *XAUUSD AI Analysis Bot*.\n"
                     "Pilih menu di bawah:",
                     reply_markup=_keyboard_menu_utama())


@bot.message_handler(commands=["analisa", "analyze"])
def cmd_analisa(m):
    if not _diizinkan(m.chat.id):
        return
    bot.send_message(m.chat.id, "⏳ Pilih timeframe:", reply_markup=_keyboard_timeframe())


@bot.message_handler(commands=["stop", "unsubscribe"])
def cmd_stop(m):
    with BROADCAST_LOCK:
        if m.chat.id in SUBSCRIBERS:
            SUBSCRIBERS.discard(m.chat.id)
            _simpan_subscribers(SUBSCRIBERS)
            bot.reply_to(m, "🔕 Anda berhenti berlangganan broadcast otomatis.")
        else:
            bot.reply_to(m, "Anda tidak sedang berlangganan.")


# --------------------------------------------------------------------------- #
# Callback (tombol inline)
# --------------------------------------------------------------------------- #
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    chat_id = c.message.chat.id
    if not _diizinkan(chat_id):
        bot.answer_callback_query(c.id, "Akses ditolak")
        return
    data = c.data

    if data == "menu":
        bot.answer_callback_query(c.id)
        bot.edit_message_text("👋 Menu utama:", chat_id, c.message.message_id,
                              reply_markup=_keyboard_menu_utama())
        return

    if data == "analisa":
        bot.answer_callback_query(c.id)
        bot.edit_message_text("⏳ Pilih timeframe:", chat_id, c.message.message_id,
                              reply_markup=_keyboard_timeframe())
        return

    if data.startswith("tf:"):
        tf = data.split(":", 1)[1]
        symbol = Settings.DEFAULT_SYMBOL
        bot.answer_callback_query(c.id, "Menganalisa... (maks ~60 detik)")
        bot.send_chat_action(chat_id, "typing")
        laporan, kb = lakukan_analisis(symbol, tf)
        _kirim_panjang(chat_id, laporan, kb)
        return

    if data.startswith("refresh:"):
        _, payload = data.split(":", 1)
        symbol, tf = payload.split("|", 1)
        bot.answer_callback_query(c.id, "Refresh...")
        bot.send_chat_action(chat_id, "typing")
        laporan, kb = lakukan_analisis(symbol, tf)
        _kirim_panjang(chat_id, laporan, kb)
        return

    if data == "seting":
        bot.answer_callback_query(c.id)
        cfg = muat()
        kb = types.InlineKeyboardMarkup(row_width=3)
        kb.add(*[types.InlineKeyboardButton(f"RR {rr}", callback_data=f"rr:{rr}")
                 for rr in ["1:2", "1:3", "1:5"]])
        kb.add(*[types.InlineKeyboardButton(kode, callback_data=f"metode:{kode}")
                 for kode, _ in METODE_ANALISIS])
        kb.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu"))
        bot.edit_message_text(
            f"⚙️ PENGATURAN SAAT INI\nRR: {cfg['risk_reward']}\nMetode: {cfg['metode_kode']} ({cfg['metode_nama']})\n\n"
            "Tekan tombol untuk mengubah:",
            chat_id, c.message.message_id, reply_markup=kb)
        return

    if data.startswith("rr:"):
        rr = data.split(":", 1)[1]
        set_rr(rr)
        bot.answer_callback_query(c.id, f"RR disimpan: {rr}", show_alert=True)
        cfg = muat()
        bot.edit_message_text(f"✅ Tersimpan: RR={cfg['risk_reward']}, Metode={cfg['metode_kode']}",
                              chat_id, c.message.message_id, reply_markup=_keyboard_menu_utama())
        return

    if data.startswith("metode:"):
        kode = data.split(":", 1)[1]
        hasil = set_metode(kode)
        if hasil:
            bot.answer_callback_query(c.id, f"Metode disimpan: {kode}", show_alert=True)
            bot.edit_message_text(f"✅ Tersimpan: Metode={hasil['metode_kode']} ({hasil['metode_nama']})",
                                  chat_id, c.message.message_id, reply_markup=_keyboard_menu_utama())
        else:
            bot.answer_callback_query(c.id, "Metode tidak valid")
        return

    if data == "status":
        bot.answer_callback_query(c.id, "Cek koneksi...")
        bot.send_chat_action(chat_id, "typing")
        from services.healthcheck import tes_semua
        baris = ["🔑 STATUS API KEY & KONEKSI"]
        for nama, ok, msg in tes_semua():
            tanda = "✅" if ok else "❌"
            baris.append(f"{tanda} {nama}: {msg}")
        cfg = muat()
        baris.append(f"\n⚙️ Pengaturan: RR={cfg['risk_reward']}, Metode={cfg['metode_kode']}")
        baris.append(f"🔔 Subscriber broadcast: {len(SUBSCRIBERS)}")
        baris.append(f"⏱️ Interval broadcast: {Settings.broadcast_interval()} menit")
        bot.edit_message_text("\n".join(baris), chat_id, c.message.message_id,
                              reply_markup=_keyboard_menu_utama())
        return

    if data == "submenu":
        bot.answer_callback_query(c.id)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🔔 Mulai Broadcast", callback_data="sub:on"),
            types.InlineKeyboardButton("🔕 Hentikan Broadcast", callback_data="sub:off"),
            types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu"),
        )
        status = "AKTIF" if chat_id in SUBSCRIBERS else "NONAKTIF"
        bot.edit_message_text(
            f"🔔 BROADCAST OTOMATIS\nStatus Anda: {status}\n"
            f"Interval: setiap {Settings.broadcast_interval()} menit (atur di .env).\n"
            f"Bot akan kirim analisa {Settings.DEFAULT_SYMBOL} otomatis.",
            chat_id, c.message.message_id, reply_markup=kb)
        return

    if data.startswith("sub:"):
        onoff = data.split(":", 1)[1]
        with BROADCAST_LOCK:
            if onoff == "on":
                SUBSCRIBERS.add(chat_id)
                _simpan_subscribers(SUBSCRIBERS)
                bot.answer_callback_query(c.id, "Broadcast AKTIF", show_alert=True)
            else:
                SUBSCRIBERS.discard(chat_id)
                _simpan_subscribers(SUBSCRIBERS)
                bot.answer_callback_query(c.id, "Broadcast dihentikan", show_alert=True)
        bot.edit_message_text("👋 Menu utama:", chat_id, c.message.message_id,
                              reply_markup=_keyboard_menu_utama())


# --------------------------------------------------------------------------- #
# Broadcast thread
# --------------------------------------------------------------------------- #
def _broadcast_loop():
    while True:
        time.sleep(Settings.broadcast_interval() * 60)
        with BROADCAST_LOCK:
            targets = list(SUBSCRIBERS)
        if not targets:
            continue
        try:
            laporan, _kb = lakukan_analisis(Settings.DEFAULT_SYMBOL, "1h")
        except Exception as e:
            laporan = f"❌ Broadcast gagal: {e}"
        for cid in targets:
            try:
                _kirim_panjang(cid, laporan)
            except Exception:
                pass


# --------------------------------------------------------------------------- #
def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Bot started. Subscribers: {len(SUBSCRIBERS)}")
    threading.Thread(target=_broadcast_loop, daemon=True).start()
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


if __name__ == "__main__":
    main()
