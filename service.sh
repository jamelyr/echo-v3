#!/bin/bash
# Echo Bot Service Management Script
# Usage: ./service.sh [install|uninstall|start|stop|status|logs]

PLIST_NAME="com.echo.bot.plist"
PLIST_SRC="/Users/marley/Documents/ag/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="/Users/marley/Documents/ag/logs"

case "$1" in
    install)
        echo "Installing Echo Bot service..."
        
        # Create logs directory
        mkdir -p "$LOG_DIR"
        
        # Copy plist to LaunchAgents
        cp "$PLIST_SRC" "$PLIST_DST"
        
        # Load the service
        launchctl load "$PLIST_DST"
        
        echo "✅ Echo Bot installed and started!"
        echo "   It will now start automatically on login."
        echo "   View logs: ./service.sh logs"
        ;;
        
    uninstall)
        echo "Uninstalling Echo Bot service..."
        
        # Unload the service
        launchctl unload "$PLIST_DST" 2>/dev/null
        
        # Remove plist
        rm -f "$PLIST_DST"
        
        echo "✅ Echo Bot service removed."
        ;;
        
    start)
        echo "Starting Echo Bot (Sleep Mode)..."
        # Note: launchctl start uses the plist arguments, which now include --sleep
        launchctl start com.echo.bot
        echo "✅ Started (Models Unloaded)"
        ;;
        
    stop)
        echo "Stopping Echo Bot..."
        launchctl stop com.echo.bot
        echo "✅ Stopped (will restart automatically due to KeepAlive)"
        ;;
        
    restart)
        echo "Restarting Echo Bot..."
        launchctl stop com.echo.bot
        sleep 2
        launchctl start com.echo.bot
        echo "✅ Restarted"
        ;;
        
    status)
        echo "Echo Bot Status:"
        launchctl list | grep com.echo.bot
        if [ $? -eq 0 ]; then
            echo "✅ Running"
        else
            echo "❌ Not running"
        fi
        ;;
        
    logs)
        echo "=== Recent Logs ==="
        echo "--- stdout ---"
        tail -50 "$LOG_DIR/echo_stdout.log" 2>/dev/null || echo "(no logs yet)"
        echo ""
        echo "--- stderr ---"
        tail -50 "$LOG_DIR/echo_stderr.log" 2>/dev/null || echo "(no logs yet)"
        ;;
        
    logs-follow)
        echo "Following logs (Ctrl+C to stop)..."
        tail -f "$LOG_DIR/echo_stdout.log" "$LOG_DIR/echo_stderr.log"
        ;;
        
    *)
        echo "Echo Bot Service Manager"
        echo ""
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|logs-follow}"
        echo ""
        echo "Commands:"
        echo "  install      Install and start the service (runs on login)"
        echo "  uninstall    Stop and remove the service"
        echo "  start        Start the service"
        echo "  stop         Stop the service"
        echo "  restart      Restart the service"
        echo "  status       Check if service is running"
        echo "  logs         Show recent logs"
        echo "  logs-follow  Follow logs in real-time"
        ;;
esac
