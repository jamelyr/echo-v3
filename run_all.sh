#!/bin/bash
# Echo V3 + BetterShift launcher (start/stop/status/logs)

set -e

ROOT_DIR="$(pwd)"
PID_DIR="$ROOT_DIR/.run_all_pids"
LOG_DIR="$ROOT_DIR/.run_all_logs"

MLX_PID_FILE="$PID_DIR/mlx.pid"
WEB_PID_FILE="$PID_DIR/web.pid"
BETTERSHIFT_PID_FILE="$PID_DIR/bettershift.pid"
WEBCTL_PID_FILE="$PID_DIR/webctl.pid"
WYGIWYH_PID_FILE="$PID_DIR/wygiwyh.pid"

MLX_LOG="$LOG_DIR/mlx_server.log"
WEB_LOG="$LOG_DIR/web_server.log"
BETTERSHIFT_LOG="$LOG_DIR/bettershift.log"
WEBCTL_LOG="$LOG_DIR/webctl.log"
WYGIWYH_LOG="$LOG_DIR/wygiwyh.log"

BETTERSHIFT_DIR="$ROOT_DIR/bettershift/BetterShift"
WYGIWYH_DIR="$ROOT_DIR/wygiwyh"

mkdir -p "$PID_DIR" "$LOG_DIR"

load_env() {
  if [ -f ".env" ]; then
    set -a  # Automatically export all variables
    source .env
    set +a  # Stop auto-exporting
  fi
}

is_running() {
  local pid_file="$1"
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_services() {
  load_env

  if is_running "$MLX_PID_FILE" || is_running "$WEB_PID_FILE" || is_running "$BETTERSHIFT_PID_FILE"; then
    echo "⚠️  One or more services are already running."
    exit 1
  fi

  echo "🚀 Starting Echo V3 + BetterShift"

  # Activate venv
  source echo_env/bin/activate

  echo "🌐 Starting webctl browser daemon..."
  nohup webctl start --mode unattended > "$WEBCTL_LOG" 2>&1 &
  echo $! > "$WEBCTL_PID_FILE"
  sleep 3

  echo "🧠 Starting MLX server..."
  nohup python mlx_server.py > "$MLX_LOG" 2>&1 &
  echo $! > "$MLX_PID_FILE"

  sleep 5

  echo "🌐 Starting Echo web server..."
  nohup python web_server.py > "$WEB_LOG" 2>&1 &
  echo $! > "$WEB_PID_FILE"

  if [ -d "$BETTERSHIFT_DIR" ]; then
    echo "📆 Starting BetterShift..."
    pushd "$BETTERSHIFT_DIR" >/dev/null
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm use 20 >/dev/null 2>&1 || true
    if [ ! -d "node_modules" ]; then
      echo "📦 Installing BetterShift dependencies..."
      npm install
    fi
    nohup npm run dev > "$BETTERSHIFT_LOG" 2>&1 &
    echo $! > "$BETTERSHIFT_PID_FILE"
    popd >/dev/null
  else
    echo "⚠️ BetterShift directory not found at $BETTERSHIFT_DIR"
  fi

  # Start WYGIWYH finance tracker
  if [ -d "$WYGIWYH_DIR" ]; then
    echo "💰 Starting WYGIWYH finance tracker..."
    pushd "$WYGIWYH_DIR" >/dev/null
    nohup python manage.py runserver 0.0.0.0:8000 > "$WYGIWYH_LOG" 2>&1 &
    echo $! > "$WYGIWYH_PID_FILE"
    popd >/dev/null
  else
    echo "⚠️ WYGIWYH directory not found at $WYGIWYH_DIR (optional)"
  fi

  echo ""
  echo "✅ Services running"
  echo "   🌐 webctl daemon: started (unattended mode)"
  echo "   🧠 MLX API:  http://127.0.0.1:1234"
  echo "   🌐 Echo UI:  http://127.0.0.1:5001"
  echo "   📆 BetterShift: http://127.0.0.1:3000"
  echo "   💰 WYGIWYH: http://127.0.0.1:8000"
}

stop_services() {
  echo "🛑 Stopping services..."

  if is_running "$WEBCTL_PID_FILE"; then
    webctl stop --daemon 2>/dev/null || true
    rm -f "$WEBCTL_PID_FILE"
  fi

  if is_running "$MLX_PID_FILE"; then
    kill "$(cat "$MLX_PID_FILE")" 2>/dev/null || true
    rm -f "$MLX_PID_FILE"
  fi
  if is_running "$WEB_PID_FILE"; then
    kill "$(cat "$WEB_PID_FILE")" 2>/dev/null || true
    rm -f "$WEB_PID_FILE"
  fi
  if is_running "$BETTERSHIFT_PID_FILE"; then
    kill "$(cat "$BETTERSHIFT_PID_FILE")" 2>/dev/null || true
    rm -f "$BETTERSHIFT_PID_FILE"
  fi
  if is_running "$WYGIWYH_PID_FILE"; then
    kill "$(cat "$WYGIWYH_PID_FILE")" 2>/dev/null || true
    rm -f "$WYGIWYH_PID_FILE"
  fi

  # Also kill any orphaned processes
  pkill -f "mlx_server.py" 2>/dev/null || true
  pkill -f "web_server.py" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  pkill -f "next-server" 2>/dev/null || true
  pkill -f "webctl" 2>/dev/null || true
  pkill -f "manage.py runserver" 2>/dev/null || true

  echo "✅ Stopped."
}

status_services() {
  echo "📊 Status"
  if is_running "$WEBCTL_PID_FILE"; then
    echo "🌐 webctl daemon: running (pid $(cat "$WEBCTL_PID_FILE"))"
  else
    echo "🌐 webctl daemon: stopped"
  fi

  if is_running "$MLX_PID_FILE"; then
    echo "🧠 MLX server: running (pid $(cat "$MLX_PID_FILE"))"
  else
    echo "🧠 MLX server: stopped"
  fi

  if is_running "$WEB_PID_FILE"; then
    echo "🌐 Echo web: running (pid $(cat "$WEB_PID_FILE"))"
  else
    echo "🌐 Echo web: stopped"
  fi

  if is_running "$BETTERSHIFT_PID_FILE"; then
    echo "📆 BetterShift: running (pid $(cat "$BETTERSHIFT_PID_FILE"))"
  else
    echo "📆 BetterShift: stopped"
  fi

  if is_running "$WYGIWYH_PID_FILE"; then
    echo "💰 WYGIWYH: running (pid $(cat "$WYGIWYH_PID_FILE"))"
  else
    echo "💰 WYGIWYH: stopped"
  fi
}

show_logs() {
  echo "📜 Logs (last 200 lines)"
  echo "--- MLX server ---"
  tail -n 200 "$MLX_LOG" 2>/dev/null || echo "(no log)"
  echo ""
  echo "--- Echo web ---"
  tail -n 200 "$WEB_LOG" 2>/dev/null || echo "(no log)"
  echo ""
  echo "--- BetterShift ---"
  tail -n 200 "$BETTERSHIFT_LOG" 2>/dev/null || echo "(no log)"
}

case "${1:-start}" in
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  restart)
    stop_services
    start_services
    ;;
  status)
    status_services
    ;;
  logs)
    show_logs
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
