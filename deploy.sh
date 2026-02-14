#!/bin/bash
# Nawwar Production Deployment Script
# Usage: ./deploy.sh [start|stop|restart|status|tunnel]
#
# This script manages the production Django server and cloudflared tunnel.
# The public URL will be printed when the tunnel starts.

PROJECT_DIR="/home/admin/Desktop/django_best_practices"
VENV_DIR="$PROJECT_DIR/venv"
GUNICORN_PID="/tmp/gunicorn-nawwar.pid"
TUNNEL_LOG="/tmp/cloudflared-nawwar.log"
PORT=8001

export DJANGO_SETTINGS_MODULE=project.settings.prod
export USE_SQLITE=true
export SECURE_COOKIES=false
export SECRET_KEY='nawwar-prod-secret-key-2024-cegco-ai-platform'

cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"

start_server() {
    echo "Starting Nawwar production server on port $PORT..."

    # Collect static files
    python manage.py collectstatic --noinput 2>/dev/null

    # Start gunicorn
    gunicorn project.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers 3 \
        --timeout 120 \
        --daemon \
        --pid "$GUNICORN_PID" \
        --access-logfile /tmp/gunicorn-nawwar-access.log \
        --error-logfile /tmp/gunicorn-nawwar-error.log

    sleep 1
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/hello/" | grep -q "200"; then
        echo "Server started successfully on port $PORT"
    else
        echo "ERROR: Server failed to start"
        return 1
    fi
}

stop_server() {
    echo "Stopping Nawwar production server..."
    if [ -f "$GUNICORN_PID" ]; then
        kill $(cat "$GUNICORN_PID") 2>/dev/null
        rm -f "$GUNICORN_PID"
    fi
    pkill -f "gunicorn project.wsgi" 2>/dev/null
    echo "Server stopped"
}

start_tunnel() {
    echo "Starting cloudflared tunnel..."
    pkill -f 'cloudflared tunnel' 2>/dev/null
    sleep 1
    nohup cloudflared tunnel --url "http://localhost:$PORT" > "$TUNNEL_LOG" 2>&1 &
    echo "Waiting for tunnel URL..."
    sleep 8
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo ""
        echo "=========================================="
        echo "  NAWWAR IS LIVE!"
        echo "=========================================="
        echo "  Public URL: $TUNNEL_URL"
        echo ""
        echo "  Key Pages:"
        echo "    Operations: $TUNNEL_URL/nawwar/operations/"
        echo "    Consumer:   $TUNNEL_URL/nawwar/consumer/"
        echo "    Home:       $TUNNEL_URL/"
        echo "    Admin:      $TUNNEL_URL/admin/"
        echo "=========================================="
    else
        echo "ERROR: Could not get tunnel URL. Check $TUNNEL_LOG"
    fi
}

show_status() {
    echo "=== Nawwar Deployment Status ==="
    if [ -f "$GUNICORN_PID" ] && kill -0 $(cat "$GUNICORN_PID") 2>/dev/null; then
        echo "Gunicorn: RUNNING (PID: $(cat $GUNICORN_PID))"
    else
        echo "Gunicorn: STOPPED"
    fi

    if pgrep -f 'cloudflared tunnel' > /dev/null; then
        TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
        echo "Tunnel: RUNNING ($TUNNEL_URL)"
    else
        echo "Tunnel: STOPPED"
    fi
}

case "${1:-start}" in
    start)
        start_server && start_tunnel
        ;;
    stop)
        pkill -f 'cloudflared tunnel' 2>/dev/null
        stop_server
        ;;
    restart)
        pkill -f 'cloudflared tunnel' 2>/dev/null
        stop_server
        sleep 1
        start_server && start_tunnel
        ;;
    server)
        start_server
        ;;
    tunnel)
        start_tunnel
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|server|tunnel|status}"
        exit 1
        ;;
esac
