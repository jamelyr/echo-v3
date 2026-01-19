#!/bin/bash
# Echo V3 Setup

echo "🔧 Echo V3 Setup"
echo ""

if [ ! -d "echo_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv echo_env
fi
source echo_env/bin/activate

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing dependencies..."
pip install uvicorn starlette httpx python-dotenv python-multipart
pip install feedparser beautifulsoup4 aiohttp playwright

echo "📦 Installing MLX..."
pip install mlx mlx-lm

echo "📦 Installing faster-whisper..."
pip install faster-whisper

echo "📦 Installing Playwright browsers..."
playwright install chromium

echo "📦 Installing MLX Embeddings..."
# Try/catch for embeddings as it can be tricky
pip install mlx-embedding-models || echo "⚠️ Could not install mlx-embedding-models via pip. Attempting fallback..."

echo ""
echo "✅ Setup complete! Run: ./run.sh"
