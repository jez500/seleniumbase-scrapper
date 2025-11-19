#!/usr/bin/env python3
"""
SeleniumBase API Server
Provides HTTP endpoints for web scraping using SeleniumBase
"""
from flask import Flask
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Cache and user scripts directories
CACHE_DIR = Path("/SeleniumBase/api/cache")
USER_SCRIPTS_DIR = Path("/SeleniumBase/api/user_scripts")
SCREENSHOTS_DIR = Path("/SeleniumBase/api/screenshots")

# Create directories if they don't exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
USER_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Environment variable defaults for scraper settings
DEFAULT_CACHE = os.getenv('DEFAULT_CACHE', 'false').lower() == 'true'
DEFAULT_FULL_CONTENT = os.getenv('DEFAULT_FULL_CONTENT', 'false').lower() == 'true'
DEFAULT_SCREENSHOT = os.getenv('DEFAULT_SCREENSHOT', 'false').lower() == 'true'
DEFAULT_USER_SCRIPTS = os.getenv('DEFAULT_USER_SCRIPTS', '')
DEFAULT_USER_SCRIPTS_TIMEOUT = int(os.getenv('DEFAULT_USER_SCRIPTS_TIMEOUT', '0'))

# Environment variable defaults for browser settings
DEFAULT_INCOGNITO = os.getenv('DEFAULT_INCOGNITO', 'true').lower() == 'true'
DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '60000'))
DEFAULT_WAIT_UNTIL = os.getenv('DEFAULT_WAIT_UNTIL', 'domcontentloaded')
DEFAULT_SLEEP = int(os.getenv('DEFAULT_SLEEP', '0'))
DEFAULT_RESOURCE = os.getenv('DEFAULT_RESOURCE', '')
DEFAULT_VIEWPORT_WIDTH = os.getenv('DEFAULT_VIEWPORT_WIDTH', '')
DEFAULT_VIEWPORT_HEIGHT = os.getenv('DEFAULT_VIEWPORT_HEIGHT', '')
DEFAULT_SCREEN_WIDTH = os.getenv('DEFAULT_SCREEN_WIDTH', '')
DEFAULT_SCREEN_HEIGHT = os.getenv('DEFAULT_SCREEN_HEIGHT', '')
DEFAULT_DEVICE = os.getenv('DEFAULT_DEVICE', 'Desktop Chrome')
DEFAULT_SCROLL_DOWN = int(os.getenv('DEFAULT_SCROLL_DOWN', '0'))
DEFAULT_IGNORE_HTTPS_ERRORS = os.getenv('DEFAULT_IGNORE_HTTPS_ERRORS', 'true').lower() == 'true'
DEFAULT_USER_AGENT = os.getenv('DEFAULT_USER_AGENT', '')
DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE', '')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', '')
DEFAULT_HTTP_CREDENTIALS = os.getenv('DEFAULT_HTTP_CREDENTIALS', '')
DEFAULT_EXTRA_HTTP_HEADERS = os.getenv('DEFAULT_EXTRA_HTTP_HEADERS', '')

# Cache TTL in seconds (default: 60 minutes)
DEFAULT_CACHE_TTL = int(os.getenv('DEFAULT_CACHE_TTL', '3600'))

# Server configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '3000'))

# Import endpoint modules
from endpoints import health, root, article

# Register all routes
health.register_routes(app)
root.register_routes(app)
article.register_routes(
    app, 
    CACHE_DIR, 
    USER_SCRIPTS_DIR, 
    SCREENSHOTS_DIR,
    DEFAULT_CACHE,
    DEFAULT_FULL_CONTENT,
    DEFAULT_SCREENSHOT,
    DEFAULT_USER_SCRIPTS,
    DEFAULT_USER_SCRIPTS_TIMEOUT,
    DEFAULT_INCOGNITO,
    DEFAULT_TIMEOUT,
    DEFAULT_WAIT_UNTIL,
    DEFAULT_SLEEP,
    DEFAULT_RESOURCE,
    DEFAULT_VIEWPORT_WIDTH,
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_SCREEN_WIDTH,
    DEFAULT_SCREEN_HEIGHT,
    DEFAULT_DEVICE,
    DEFAULT_SCROLL_DOWN,
    DEFAULT_IGNORE_HTTPS_ERRORS,
    DEFAULT_USER_AGENT,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE,
    DEFAULT_HTTP_CREDENTIALS,
    DEFAULT_EXTRA_HTTP_HEADERS,
    DEFAULT_CACHE_TTL
)


if __name__ == '__main__':
    # Run Flask app with configurable host and port
    logger.info(f"Starting server on {API_HOST}:{API_PORT}")
    app.run(host=API_HOST, port=API_PORT, debug=False)
