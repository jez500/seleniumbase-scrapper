#!/bin/bash
set -e

# Read environment variables with defaults
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-3000}"

echo "***** SeleniumBase Docker Machine with API *****"
echo "Starting SeleniumBase API Server on ${API_HOST}:${API_PORT}..."

# If no command specified or bash is specified, run API server in foreground
if [ "$#" -eq 0 ] || [ "$1" = "/bin/bash" ]; then
    echo "API available at http://${API_HOST}:${API_PORT}"
    echo "Endpoints:"
    echo "  - GET /api/article?url=<URL>"
    echo "  - GET /health"
    echo "  - GET /"
    # Run API server in foreground to keep container alive
    exec python3 /SeleniumBase/api/server.py
else
    # If another command is specified, execute it
    exec "$@"
fi
