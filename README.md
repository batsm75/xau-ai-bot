# 🤖 XAUUSD AI Analysis Telegram Bot

Bot Telegram untuk analisa **XAUUSD (Emas)** real-time: data market dari **TwelveData** (+SoSoValue),
indikator teknikal **EMA/RSI/MACD/Bollinger/ATR** (murni Python, tanpa TA-Lib), scraping berita
ekonomi via **BeautifulSoup4**, dan otak AI **Gemini** (fallback otomatis ke **Deatcode/GPT** saat limit).

> ⚠️ Edukasi saja, bukan saran investasi.

## ✨ Fitur
- 📊 **Analisa teknikal** otomatis (EMA, RSI, MACD, Bollinger Bands, ATR)
- 📰 **Analisa fundamental** — berita ekonomi/gold terbaru (scraping RSS)
- 🧠 **AI summary & rekomendasi** — Gemini (auto-switch model) + fallback Deatcode
- ⚖️ **Risk management** — entry/SL/TP dihitung sesuai Risk:Reward pilihan
- 🔔 **Broadcast otomatis** — kirim analisa tiap N menit ke subscriber
- 🔑 **Cek status koneksi** semua provider langsung dari bot
- 📱 Jalan di **Termux (HP)** dan Linux

## 🛠️ Tech Stack
Python 3.9+ · pyTelegramBotAPI · Twelve Data API · BeautifulSoup4 · requests · python-dotenv

## 📦 Instalasi (Termux / Linux)
```bash
pkg install -y python git          # Termux
git clone <repo> && cd xau-ai-bot
pip install -r requirements.txt
cp .env.example .env
# Isi .env: TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, TWELVEDATA_API_KEY
python bot.py
```

## ⚙️ Konfigurasi (.env)
| Variabel | Fungsi |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token dari **@BotFather** (wajib) |
| `ALLOWED_USER_IDS` | User ID yang boleh pakai bot (kosong = publik) |
| `DEFAULT_SYMBOL` | Default `XAU/USD` |
| `BROADCAST_INTERVAL_MIN` | Interval broadcast (default 30, min 5) |
| `GEMINI_API_KEY` | Otak AI utama (aistudio.google.com) |
| `DEATCODE_API_KEY` | Cadangan (console.deatcode.com, butuh kredit) |
| `TWELVEDATA_API_KEY` | Data market (wajib) |

## 🎮 Perintah & Tombol
- `/start` — menu utama (tombol: Analisa, Pengaturan, Status, Broadcast)
- **Analisa** → pilih timeframe (15m/30m/1h/4h/1d) → laporan lengkap + tombol 🔄 Refresh
- **Pengaturan** → set Risk:Reward (1:2/1:3/1:5) + metode (SND/SNR/SMC/ICT/Killzone)
- **Status** → cek API key & koneksi semua provider
- **Broadcast** → 🔔 mulai / 🔕 hentikan kirim otomatis
- `/stop` — berhenti berlangganan

## 📁 Struktur
```
xau-ai-bot/
├── bot.py                 # entry point + handler Telegram
├── requirements.txt
├── .env.example
├── config/settings.py     # load .env
├── core/trade_config.py   # simpan RR & metode (config.json)
├── services/
│   ├── ai_analyzer.py     # Gemini -> Deatcode fallback
│   ├── market_data.py     # TwelveData + SoSoValue
│   ├── indicators.py      # EMA/RSI/MACD/BB/ATR
│   ├── news.py            # scraping berita (BS4)
│   └── healthcheck.py     # tes koneksi provider
└── storage/               # config.json + subscribers.json
```

## 🧪 Test
```bash
python tests/test_smoke.py
```
