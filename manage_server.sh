#!/bin/bash

APP_DIR="/home/ec2-user/leapmind_index"
APP_MODULE="service:app"
HOST="0.0.0.0"
PORT="8000"
LOG_DIR="$APP_DIR/log"
PID_FILE="$LOG_DIR/uvicorn.pid"
LOG_FILE="$LOG_DIR/server.log"

cd "$APP_DIR"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Server already running (PID $(cat $PID_FILE))"
        exit 1
    fi
    nohup uvicorn $APP_MODULE --host $HOST --port $PORT > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Server started (PID $!)"
}

stop() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        kill $(cat "$PID_FILE")
        rm "$PID_FILE"
        echo "Server stopped (by PID file)"
    else
        PID_ON_PORT=$(lsof -ti :$PORT)
        if [ ! -z "$PID_ON_PORT" ]; then
            kill $PID_ON_PORT
            echo "Killed process on port $PORT (PID $PID_ON_PORT)"
        else
            echo "Server not running"
        fi
    fi
}

restart() {
    stop
    start
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Server is running (PID $(cat $PID_FILE))"
    else
        echo "Server is not running"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart|rerun)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|rerun|status}"
        exit 1
        ;;
esac