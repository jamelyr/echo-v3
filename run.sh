#!/bin/bash
# Echo V3 Launcher

echo "🚀 Echo V3 Starting..."

# Kill any existing
pkill -f "mlx_server.py" 2>/dev/null
pkill -f "web_server.py" 2>/dev/null
sleep 1

# Activate venv
source echo_env/bin/activate

# Start MLX Server
echo "🧠 Starting Intelligence Engine..."
python mlx_server.py &
MLX_PID=$!

# Wait for model to load
echo "⏳ Waiting for model..."
sleep 5

# Start Web Server
echo "🌐 Starting Web Interface..."
python web_server.py &
WEB_PID=$!

echo ""
echo "✅ Echo V3 Online!"
echo "   📱 Web UI:  http://localhost:5001"
echo "   🧠 MLX API: http://127.0.0.1:1234"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $MLX_PID $WEB_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
