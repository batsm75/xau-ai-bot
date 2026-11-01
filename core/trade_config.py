"""Pengaturan trade global (RR + metode analisis) — disimpan ke storage/config.json."""
from __future__ import annotations

import json
from pathlib import Path

from config.settings import CONFIG_JSON

METODE_ANALISIS: list[tuple[str, str]] = [
    ("SND", "Supply & Demand"),
    ("SNR", "Support & Resistance"),
    ("SMC", "Smart Money Concepts"),
    ("ICT", "Inner Circle Trader"),
    ("SESSION KILLZONE", "Session Killzone"),
]

DEFAULT = {"risk_reward": "1:2", "metode_kode": "SMC", "metode_nama": "Smart Money Concepts"}


def muat() -> dict:
    if Path(CONFIG_JSON).exists():
        try:
            return {**DEFAULT, **json.loads(Path(CONFIG_JSON).read_text())}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT)


def simpan(cfg: dict) -> None:
    Path(CONFIG_JSON).write_text(json.dumps(cfg, indent=2))


def set_rr(rr: str) -> dict:
    cfg = muat()
    cfg["risk_reward"] = rr
    simpan(cfg)
    return cfg


def set_metode(kode: str) -> dict | None:
    for k, nama in METODE_ANALISIS:
        if k == kode:
            cfg = muat()
            cfg["metode_kode"] = k
            cfg["metode_nama"] = nama
            simpan(cfg)
            return cfg
    return None
