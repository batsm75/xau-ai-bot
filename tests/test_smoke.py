"""Smoke test bot Telegram. Jalankan: python tests/test_smoke.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_imports():
    import config.settings
    import services.ai_analyzer
    import services.market_data
    import services.indicators
    import services.news
    import services.healthcheck
    import core.trade_config
    import telebot  # noqa
    import bs4    # noqa

def test_indikator():
    from services.indicators import hitung_indikator
    candles = [{"open": float(100+i), "high": float(102+i), "low": float(98+i), "close": float(101+i)} for i in range(60)]
    ind = hitung_indikator(candles)
    assert ind["harga"] == 160.0
    assert ind["rsi"] is not None
    assert ind["ema20"] is not None
    assert "teks" in ind

def test_trade_config():
    from core.trade_config import set_rr, set_metode, muat
    set_rr("1:3")
    assert muat()["risk_reward"] == "1:3"
    set_metode("ICT")
    assert muat()["metode_kode"] == "ICT"
    set_rr("1:2"); set_metode("SMC")  # pulihkan

if __name__ == "__main__":
    test_imports(); test_indikator(); test_trade_config()
    print("SEMUA SMOKE TEST BOT LULUS ✓")
