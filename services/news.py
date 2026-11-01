"""Ambil berita ekonomi/gold terbaru via RSS + BeautifulSoup4.

Graceful: jika semua sumber gagal, return list kosong — analisis tetap jalan
tanpa bagian fundamental. Tidak ada dependency berat.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

TIMEOUT = 12
USER_AGENT = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

# Sumber RSS berita (dicoba berurutan, pakai yang pertama berhasil)
SUMBER_RSS = [
    "https://www.investing.com/rss/news_25.rss",      # Gold & Metals
    "https://www.investing.com/rss/news_1.rss",       # Economic
    "https://www.forexlive.com/feed/",
    "https://www.dailyfx.com/feeds/all",
]


def _parse_rss(xml_text: str, maks: int = 5) -> list[str]:
    soup = BeautifulSoup(xml_text, "html.parser")
    items = soup.find_all("item")[:maks]
    hasil = []
    for it in items:
        title = it.find("title")
        if title and title.get_text(strip=True):
            hasil.append(title.get_text(strip=True))
    return hasil


def ambil_berita(maks: int = 5) -> list[str]:
    for url in SUMBER_RSS:
        try:
            r = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
            if r.status_code != 200 or len(r.text) < 200:
                continue
            judul = _parse_rss(r.text, maks)
            if judul:
                return judul
        except Exception:
            continue
    return []


def format_untuk_ai(berita: list[str]) -> str:
    if not berita:
        return "BERITA: tidak berhasil diambil (lewati bagian fundamental)."
    return "BERITA EKONOMI/GOLD TERBARU:\n" + "\n".join(f"- {b}" for b in berita)
