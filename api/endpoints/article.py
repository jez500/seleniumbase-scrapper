#!/usr/bin/env python3
"""
Article endpoint for SeleniumBase API
"""
from flask import request, jsonify
from seleniumbase import Driver
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import logging
import hashlib
import time
import os

# Import helper functions
from helpers import (
    get_cache_key, get_cached_result, save_to_cache,
    parse_bool_param, parse_int_param, parse_list_param,
    extract_meta_tags, extract_article_content, 
    extract_text_content, extract_published_time
)

logger = logging.getLogger(__name__)


def register_routes(app, cache_dir, user_scripts_dir, screenshots_dir, 
                    default_cache, default_full_content, default_screenshot,
                    default_user_scripts, default_user_scripts_timeout,
                    default_incognito, default_timeout, default_wait_until,
                    default_sleep, default_resource, default_viewport_width,
                    default_viewport_height, default_screen_width, default_screen_height,
                    default_device, default_scroll_down, default_ignore_https_errors,
                    default_user_agent, default_locale, default_timezone,
                    default_http_credentials, default_extra_http_headers,
                    default_cache_ttl):
    """Register article routes with the Flask app"""
    
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
            use_cache = parse_bool_param(request.args.get('cache'), default_cache)
            full_content = parse_bool_param(request.args.get('full-content'), default_full_content)
            screenshot = parse_bool_param(request.args.get('screenshot'), default_screenshot)
            user_scripts = parse_list_param(request.args.get('user-scripts'), default_user_scripts)
            user_scripts_timeout = parse_int_param(request.args.get('user-scripts-timeout'), default_user_scripts_timeout)
            
            # Parse browser parameters
            incognito = parse_bool_param(request.args.get('incognito'), default_incognito)
            timeout = parse_int_param(request.args.get('timeout'), default_timeout)
            wait_until = request.args.get('wait-until', default_wait_until)
            sleep_time = parse_int_param(request.args.get('sleep'), default_sleep)
            resource_filter = parse_list_param(request.args.get('resource'), default_resource)
            viewport_width = parse_int_param(request.args.get('viewport-width'), None) if request.args.get('viewport-width', default_viewport_width) else None
            viewport_height = parse_int_param(request.args.get('viewport-height'), None) if request.args.get('viewport-height', default_viewport_height) else None
            screen_width = parse_int_param(request.args.get('screen-width'), None) if request.args.get('screen-width', default_screen_width) else None
            screen_height = parse_int_param(request.args.get('screen-height'), None) if request.args.get('screen-height', default_screen_height) else None
            device = request.args.get('device', default_device)
            scroll_down = parse_int_param(request.args.get('scroll-down'), default_scroll_down)
            ignore_https_errors = parse_bool_param(request.args.get('ignore-https-errors'), default_ignore_https_errors)
            user_agent = request.args.get('user-agent', default_user_agent)
            locale = request.args.get('locale', default_locale)
            timezone = request.args.get('timezone', default_timezone)
            http_credentials = request.args.get('http-credentials', default_http_credentials)
            extra_http_headers = request.args.get('extra-http-headers', default_extra_http_headers)
            
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
                cached_result = get_cached_result(cache_key, cache_dir, default_cache_ttl)
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
                'binary_location': '/usr/bin/chromedriver',
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
                        script_path = user_scripts_dir / script_name
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
                        screenshot_path = screenshots_dir / screenshot_filename
                        
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
            save_to_cache(cache_key, response, cache_dir)
            
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
