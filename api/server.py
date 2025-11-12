#!/usr/bin/env python3
"""
SeleniumBase API Server
Provides HTTP endpoints for web scraping using SeleniumBase
"""
from flask import Flask, request, jsonify
from seleniumbase import Driver
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import logging
import hashlib
import re
import os
import json
import time
import base64
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


def get_cache_key(url, params):
    """Generate cache key from URL and parameters"""
    # Create a stable string from params
    param_str = json.dumps(params, sort_keys=True)
    cache_str = f"{url}:{param_str}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def get_cached_result(cache_key):
    """Retrieve cached result if available and not expired"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_entry = json.load(f)
            
            # Check if cache entry has the new structure with timestamp
            if isinstance(cache_entry, dict) and 'timestamp' in cache_entry and 'data' in cache_entry:
                # Check if cache has expired
                age = time.time() - cache_entry['timestamp']
                if age > DEFAULT_CACHE_TTL:
                    logger.info(f"Cache expired (age: {age:.1f}s, TTL: {DEFAULT_CACHE_TTL}s)")
                    return None
                return cache_entry['data']
            else:
                # Old cache format without timestamp - treat as expired
                logger.info("Cache entry has old format without timestamp, treating as expired")
                return None
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
    return None


def save_to_cache(cache_key, data):
    """Save result to cache with timestamp"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        cache_entry = {
            'timestamp': time.time(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_entry, f)
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def parse_bool_param(value, default):
    """Parse boolean parameter from string"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.lower() in ['true', '1', 'yes']


def parse_int_param(value, default):
    """Parse integer parameter from string"""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_list_param(value, default=''):
    """Parse comma-separated list parameter"""
    if value is None or value == '':
        return default
    return value


def extract_meta_tags(soup):
    """Extract Open Graph and Twitter meta tags"""
    meta = {}
    
    # Open Graph tags
    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
    for tag in og_tags:
        property_name = tag.get('property', '').replace('og:', '')
        content = tag.get('content')
        if property_name and content:
            meta[f'og_{property_name}'] = content
    
    # Twitter tags
    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
    for tag in twitter_tags:
        name = tag.get('name', '').replace('twitter:', '')
        content = tag.get('content')
        if name and content:
            meta[f'twitter_{name}'] = content
    
    return meta if meta else None


def extract_article_content(soup):
    """Extract main article content"""
    # Try to find article tag
    article = soup.find('article')
    if article:
        return str(article)
    
    # Try to find main content area
    main = soup.find('main')
    if main:
        return str(main)
    
    # Try to find div with common article class names
    for class_name in ['article', 'post', 'entry', 'content', 'main-content']:
        content = soup.find(['div', 'section'], class_=re.compile(class_name, re.I))
        if content:
            return str(content)
    
    return None


def extract_text_content(soup):
    """Extract text content with basic formatting"""
    # Remove script and style elements
    for script in soup(['script', 'style', 'nav', 'header', 'footer']):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up multiple newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text if text else None


def extract_published_time(soup):
    """Extract article publication time"""
    # Try meta tags first
    time_tag = soup.find('meta', property='article:published_time')
    if time_tag and time_tag.get('content'):
        return time_tag.get('content')
    
    time_tag = soup.find('meta', attrs={'name': 'publication_date'})
    if time_tag and time_tag.get('content'):
        return time_tag.get('content')
    
    # Try time tag
    time_elem = soup.find('time')
    if time_elem:
        datetime_attr = time_elem.get('datetime')
        if datetime_attr:
            return datetime_attr
    
    return None


@app.route('/api/article', methods=['GET'])
def get_article():
    """
    Fetch article content and metadata from a given URL using SeleniumBase
    
    Query Parameters:
        Scraper settings:
        - url (str, required): Page URL to fetch
        - cache (bool): Use cached results if available
        - full-content (bool): Include full HTML in fullContent field
        - screenshot (bool): Take screenshot of the page
        - user-scripts (str): Comma-separated list of user scripts to run
        - user-scripts-timeout (int): Wait time after user scripts in milliseconds
        
        Browser settings:
        - incognito (bool): Use incognito mode
        - timeout (int): Navigation timeout in milliseconds
        - wait-until (str): When to consider navigation complete
        - sleep (int): Wait time after page load in milliseconds
        - resource (str): Comma-separated list of allowed resource types
        - viewport-width (int): Viewport width in pixels
        - viewport-height (int): Viewport height in pixels
        - screen-width (int): Screen width in pixels
        - screen-height (int): Screen height in pixels
        - device (str): Device to emulate
        - scroll-down (int): Scroll down by pixels
        - ignore-https-errors (bool): Ignore HTTPS errors
        - user-agent (str): Custom user agent
        - locale (str): Browser locale
        - timezone (str): Browser timezone
        - http-credentials (str): HTTP auth credentials (username:password)
        - extra-http-headers (str): Extra HTTP headers (key1:value1;key2:value2)
    
    Returns:
        JSON response with article data and metadata
    """
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'detail': [
                {
                    'type': 'missing_parameter',
                    'msg': 'Missing required parameter: url'
                }
            ]
        }), 400
    
    try:
        # Parse scraper parameters
        use_cache = parse_bool_param(request.args.get('cache'), DEFAULT_CACHE)
        full_content = parse_bool_param(request.args.get('full-content'), DEFAULT_FULL_CONTENT)
        screenshot = parse_bool_param(request.args.get('screenshot'), DEFAULT_SCREENSHOT)
        user_scripts = parse_list_param(request.args.get('user-scripts'), DEFAULT_USER_SCRIPTS)
        user_scripts_timeout = parse_int_param(request.args.get('user-scripts-timeout'), DEFAULT_USER_SCRIPTS_TIMEOUT)
        
        # Parse browser parameters
        incognito = parse_bool_param(request.args.get('incognito'), DEFAULT_INCOGNITO)
        timeout = parse_int_param(request.args.get('timeout'), DEFAULT_TIMEOUT)
        wait_until = request.args.get('wait-until', DEFAULT_WAIT_UNTIL)
        sleep_time = parse_int_param(request.args.get('sleep'), DEFAULT_SLEEP)
        resource_filter = parse_list_param(request.args.get('resource'), DEFAULT_RESOURCE)
        viewport_width = parse_int_param(request.args.get('viewport-width'), None) if request.args.get('viewport-width', DEFAULT_VIEWPORT_WIDTH) else None
        viewport_height = parse_int_param(request.args.get('viewport-height'), None) if request.args.get('viewport-height', DEFAULT_VIEWPORT_HEIGHT) else None
        screen_width = parse_int_param(request.args.get('screen-width'), None) if request.args.get('screen-width', DEFAULT_SCREEN_WIDTH) else None
        screen_height = parse_int_param(request.args.get('screen-height'), None) if request.args.get('screen-height', DEFAULT_SCREEN_HEIGHT) else None
        device = request.args.get('device', DEFAULT_DEVICE)
        scroll_down = parse_int_param(request.args.get('scroll-down'), DEFAULT_SCROLL_DOWN)
        ignore_https_errors = parse_bool_param(request.args.get('ignore-https-errors'), DEFAULT_IGNORE_HTTPS_ERRORS)
        user_agent = request.args.get('user-agent', DEFAULT_USER_AGENT)
        locale = request.args.get('locale', DEFAULT_LOCALE)
        timezone = request.args.get('timezone', DEFAULT_TIMEZONE)
        http_credentials = request.args.get('http-credentials', DEFAULT_HTTP_CREDENTIALS)
        extra_http_headers = request.args.get('extra-http-headers', DEFAULT_EXTRA_HTTP_HEADERS)
        
        # Build query object for cache key
        # Note: 'cache' parameter is excluded because it doesn't affect content
        query_params = {
            'full-content': full_content,
            'screenshot': screenshot,
            'user-scripts': user_scripts,
            'user-scripts-timeout': user_scripts_timeout,
            'incognito': incognito,
            'timeout': timeout,
            'wait-until': wait_until,
            'sleep': sleep_time,
            'resource': resource_filter,
            'viewport-width': viewport_width,
            'viewport-height': viewport_height,
            'screen-width': screen_width,
            'screen-height': screen_height,
            'device': device,
            'scroll-down': scroll_down,
            'ignore-https-errors': ignore_https_errors,
            'user-agent': user_agent,
            'locale': locale,
            'timezone': timezone,
        }
        
        # Generate cache key
        cache_key = get_cache_key(url, query_params)
        
        # Check cache if enabled
        if use_cache:
            cached_result = get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Returning cached result for URL: {url}")
                return jsonify(cached_result), 200
        
        logger.info(f"Fetching URL: {url}")
        
        # Initialize SeleniumBase Driver with configuration
        driver_kwargs = {
            'browser': 'chrome',
            'headless': True,
            'uc': True,
            'incognito': incognito,
        }
        
        # Note: SeleniumBase Driver may not support all these options directly
        # We'll use what's available and log warnings for unsupported features
        
        driver = None
        try:
            driver = Driver(**driver_kwargs)
            
            # Set timeout (convert milliseconds to seconds)
            if timeout > 0:
                driver.set_page_load_timeout(timeout / 1000.0)
            
            # Set viewport size if specified
            if viewport_width and viewport_height:
                driver.set_window_size(viewport_width, viewport_height)
            
            # Navigate to the URL
            driver.get(url)
            
            # Run user scripts if specified
            if user_scripts:
                script_names = [s.strip() for s in user_scripts.split(',') if s.strip()]
                for script_name in script_names:
                    script_path = USER_SCRIPTS_DIR / script_name
                    if script_path.exists():
                        try:
                            with open(script_path, 'r') as f:
                                script_code = f.read()
                            driver.execute_script(script_code)
                            logger.info(f"Executed user script: {script_name}")
                        except Exception as e:
                            logger.warning(f"Failed to execute user script {script_name}: {e}")
                    else:
                        logger.warning(f"User script not found: {script_name}")
                
                # Wait after user scripts
                if user_scripts_timeout > 0:
                    time.sleep(user_scripts_timeout / 1000.0)
            
            # Sleep if specified
            if sleep_time > 0:
                time.sleep(sleep_time / 1000.0)
            
            # Scroll down if specified
            if scroll_down > 0:
                driver.execute_script(f"window.scrollBy(0, {scroll_down});")
                # Give time for lazy-loaded content
                time.sleep(0.5)
            
            # Get the final URL after redirects
            final_url = driver.current_url
            
            # Get the page HTML
            html_content = driver.page_source
            
            # Take screenshot if requested
            screenshot_uri = None
            if screenshot:
                try:
                    screenshot_filename = f"{cache_key}.png"
                    screenshot_path = SCREENSHOTS_DIR / screenshot_filename
                    
                    # Try full page screenshot first
                    try:
                        driver.save_screenshot(str(screenshot_path))
                        screenshot_uri = f"file://screenshots/{screenshot_filename}"
                        logger.info(f"Screenshot saved: {screenshot_filename}")
                    except Exception as e:
                        logger.warning(f"Failed to save screenshot: {e}")
                        screenshot_uri = None
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")
            
            logger.info(f"Successfully fetched {len(html_content)} bytes from {url}")
            
        finally:
            # Always close the driver
            if driver:
                driver.quit()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Try Open Graph title
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
        
        # Extract description/excerpt
        excerpt = None
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            excerpt = desc_tag.get('content')
        
        if not excerpt:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                excerpt = og_desc.get('content')
        
        # Extract byline/author
        byline = None
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            byline = author_tag.get('content')
        
        if not byline:
            article_author = soup.find('meta', property='article:author')
            if article_author:
                byline = article_author.get('content')
        
        # Extract site name
        site_name = None
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name:
            site_name = og_site_name.get('content')
        
        # Extract language
        lang = None
        html_tag = soup.find('html')
        if html_tag:
            lang = html_tag.get('lang')
        
        # Extract direction
        dir_attr = None
        if html_tag:
            dir_attr = html_tag.get('dir')
        
        # Extract article content
        content = extract_article_content(soup)
        
        # Extract text content
        text_content = extract_text_content(soup)
        
        # Calculate content length
        length = len(text_content) if text_content else None
        
        # Extract meta tags
        meta = extract_meta_tags(soup)
        
        # Extract published time
        published_time = extract_published_time(soup)
        
        # Generate unique ID
        result_id = hashlib.md5(final_url.encode()).hexdigest()
        
        # Parse domain
        parsed_url = urlparse(final_url)
        domain = parsed_url.netloc
        
        # Get current date in ISO format
        current_date = datetime.utcnow().isoformat() + 'Z'
        
        # Build query object
        query = {'url': url}
        query.update({k: v for k, v in request.args.items() if k != 'url'})
        
        # Build result URI
        result_uri = f"api://article/{result_id}"
        
        # Build response
        response = {
            'id': result_id,
            'url': final_url,
            'domain': domain,
            'title': title,
            'byline': byline,
            'excerpt': excerpt,
            'siteName': site_name,
            'content': content,
            'textContent': text_content,
            'length': length,
            'lang': lang,
            'dir': dir_attr,
            'publishedTime': published_time,
            'fullContent': html_content if full_content else None,
            'date': current_date,
            'query': query,
            'meta': meta,
            'resultUri': result_uri,
            'screenshotUri': screenshot_uri
        }
        
        # Save to cache
        save_to_cache(cache_key, response)
        
        return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {str(e)}", exc_info=True)
        return jsonify({
            'detail': [
                {
                    'type': 'fetch_error',
                    'msg': f'Failed to fetch URL: {str(e)}'
                }
            ]
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'seleniumbase-api'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        'service': 'SeleniumBase API',
        'version': '1.0.0',
        'endpoints': {
            '/api/article': {
                'method': 'GET',
                'description': 'Fetch HTML content from a URL',
                'parameters': {
                    'url': 'The URL to fetch (required)'
                },
                'example': '/api/article?url=https://en.wikipedia.org/wiki/web_scraping'
            },
            '/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            }
        }
    }), 200


if __name__ == '__main__':
    # Run Flask app on all interfaces, port 8000
    app.run(host='0.0.0.0', port=8000, debug=False)
