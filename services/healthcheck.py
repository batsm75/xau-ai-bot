"""Tes koneksi ringan ke setiap provider (endpoint gratis).

Dipanggil dari tombol "Status API" di bot.
"""
from __future__ import annotations

import requests

from config.settings import Settings

TIMEOUT = 15


def _ok(msg: str): return True, msg
def _gagal(msg: str): return False, msg


def tes_groq() -> tuple[bool, str]:
    if not Settings.GROQ_API_KEY:
        return _gagal("API key kosong — dapatkan gratis di console.groq.com/keys")
    url = f"{Settings.GROQ_BASE_URL.rstrip('/')}/models"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {Settings.GROQ_API_KEY}"}, timeout=TIMEOUT)
        if r.status_code == 200:
            return _ok(f"terhubung (gratis) — model {Settings.GROQ_MODEL}")
        return _gagal(f"HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        return _gagal(f"koneksi gagal: {type(e).__name__}")


def tes_twelvedata() -> tuple[bool, str]:
    if not Settings.TWELVEDATA_API_KEY:
        return _gagal("API key kosong")
    try:
        r = requests.get(
            f"{Settings.TWELVEDATA_BASE_URL.rstrip('/')}/api_usage",
            params={"apikey": Settings.TWELVEDATA_API_KEY}, timeout=TIMEOUT,
        )
        if r.status_code == 200 and "message" not in r.json():
            d = r.json()
            return _ok(f"terhubung — pemakaian {d.get('current_usage','?')}/{d.get('plan_limit','?')} request/hari")
        return _gagal(f"HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        return _gagal(f"koneksi gagal: {type(e).__name__}")


def tes_sosovalue() -> tuple[bool, str]:
    if not Settings.SOSOVALUE_API_KEY:
        return _gagal("API key kosong (opsional)")
    try:
        r = requests.get(
            f"{Settings.SOSOVALUE_BASE_URL.rstrip('/')}/currencies",
            headers={"Accept": "application/json", "x-soso-api-key": Settings.SOSOVALUE_API_KEY},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return _ok("terhubung")
        return _gagal(f"HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        return _gagal(f"koneksi gagal: {type(e).__name__}")


def tes_semua() -> list[tuple[str, bool, str]]:
    return [
        ("Groq (otak AI)", *tes_groq()),
        ("TwelveData", *tes_twelvedata()),
        ("SoSoValue", *tes_sosovalue()),
    ]
