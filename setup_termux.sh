#!/data/data/com.termux/files/usr/bin/bash
# Setup one-command untuk Termux.
# Pakai:  bash setup_termux.sh
set -e

echo "==> Install dependencies sistem (python, git)..."
pkg update -y && pkg upgrade -y
pkg install -y python git

echo "==> Install library Python..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Membuat .env dari .env.example..."
  cp .env.example .env
fi

echo ""
echo "SELESAI. Jalankan aplikasi dengan:"
echo "  python run.py"
echo ""
echo "Lalu buka menu '3. Env' untuk mengisi API key Anda."
