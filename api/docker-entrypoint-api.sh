#!/bin/bash
set -e
echo "***** SeleniumBase Docker Machine with API *****"
echo "Starting SeleniumBase API Server on port 8000..."

# If no command specified or bash is specified, run API server in foreground
if [ "$#" -eq 0 ] || [ "$1" = "/bin/bash" ]; then
    echo "API available at http://0.0.0.0:8000"
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
