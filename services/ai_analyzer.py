"""Otak AI: Groq (Llama 3.3 70B) — satu-satunya provider.

Gratis selamanya (rate limit per menit, tanpa kartu kredit).
Dapatkan key: https://console.groq.com/keys
Endpoint OpenAI-compatible: https://api.groq.com/openai/v1
"""
from __future__ import annotations

import json

import requests

from config.settings import Settings

REQUEST_TIMEOUT = 60


class AIServiceError(Exception):
    """Provider AI gagal dipakai."""


class AIAnalyzer:
    def __init__(self) -> None:
        self.provider_terakhir: str = "belum ada"

    def analisis(self, prompt: str, system: str) -> tuple[str, str]:
        """Kembalikan (teks_analisis, nama_provider)."""
        if not Settings.GROQ_API_KEY:
            raise AIServiceError(
                "GROQ_API_KEY kosong. Dapatkan gratis (tanpa kartu kredit) di "
                "https://console.groq.com/keys lalu isi di file .env"
            )

        url = f"{Settings.GROQ_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Settings.GROQ_API_KEY}",
        }
        body = {
            "model": Settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise AIServiceError(f"Koneksi ke Groq gagal: {e}")

        if resp.status_code == 429:
            raise AIServiceError(
                "Groq kena rate limit (429) — quota gratis per menit. "
                "Tunggu ~1 menit lalu coba lagi (tekan Refresh)."
            )
        if resp.status_code >= 400:
            raise AIServiceError(f"Groq HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            hasil = resp.json()["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            raise AIServiceError(f"Format respons Groq tidak dikenali: {resp.text[:300]}")

        self.provider_terakhir = f"Groq {Settings.GROQ_MODEL}"
        return hasil, self.provider_terakhir
