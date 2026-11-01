"""Manajemen konfigurasi: memuat .env dan menyediakan akses terpusat.

Otak AI: Groq saja (gratis selamanya, tanpa kartu kredit).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
ENV_PATH: Path = ROOT_DIR / ".env"
STORAGE_DIR: Path = ROOT_DIR / "storage"
CONFIG_JSON: Path = STORAGE_DIR / "config.json"
SUBSCRIBERS_JSON: Path = STORAGE_DIR / "subscribers.json"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ENV_FIELDS: list[tuple[str, str, str]] = [
    ("TELEGRAM_BOT_TOKEN",   "Telegram Bot Token (@BotFather)",     ""),
    ("ALLOWED_USER_IDS",     "User ID diizinkan (koma, kosong=public)", ""),
    ("DEFAULT_SYMBOL",       "Instrumen default",                   "XAU/USD"),
    ("BROADCAST_INTERVAL_MIN","Interval broadcast (menit)",         "30"),
    ("GROQ_API_KEY",         "Groq API Key (otak AI, gratis)",      ""),
    ("GROQ_MODEL",           "Groq Model",                          "llama-3.3-70b-versatile"),
    ("GROQ_BASE_URL",        "Groq Base URL",                       "https://api.groq.com/openai/v1"),
    ("TWELVEDATA_API_KEY",   "TwelveData API Key (market data)",    ""),
    ("TWELVEDATA_BASE_URL",  "TwelveData Base URL",                 "https://api.twelvedata.com"),
    ("SOSOVALUE_API_KEY",    "SoSoValue API Key (opsional)",        ""),
    ("SOSOVALUE_BASE_URL",   "SoSoValue Base URL",                  "https://openapi.sosovalue.com/openapi/v1"),
    ("SOSOVALUE_KLINE_PATH", "SoSoValue Kline Path",                "/currency/historical-klines"),
]


class Settings:
    TELEGRAM_BOT_TOKEN: str = ""
    ALLOWED_USER_IDS: str = ""
    DEFAULT_SYMBOL: str = "XAU/USD"
    BROADCAST_INTERVAL_MIN: str = "30"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    TWELVEDATA_API_KEY: str = ""
    TWELVEDATA_BASE_URL: str = "https://api.twelvedata.com"
    SOSOVALUE_API_KEY: str = ""
    SOSOVALUE_BASE_URL: str = "https://openapi.sosovalue.com/openapi/v1"
    SOSOVALUE_KLINE_PATH: str = "/currency/historical-klines"

    @classmethod
    def reload(cls) -> None:
        load_dotenv(ENV_PATH, override=True)
        for key, _label, default in ENV_FIELDS:
            setattr(cls, key, os.getenv(key, default))

    @classmethod
    def allowed_user_ids(cls) -> list[int]:
        raw = (cls.ALLOWED_USER_IDS or "").strip()
        if not raw:
            return []
        out = []
        for x in raw.split(","):
            x = x.strip()
            if x.isdigit():
                out.append(int(x))
        return out

    @classmethod
    def broadcast_interval(cls) -> int:
        try:
            return max(5, int(cls.BROADCAST_INTERVAL_MIN))
        except ValueError:
            return 30


Settings.reload()
