#!/usr/bin/env python3
"""
Helper functions for SeleniumBase API Server
Contains utility functions for caching, parameter parsing, and HTML extraction
"""
from bs4 import BeautifulSoup
import hashlib
import re
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_cache_key(url, params):
    """Generate cache key from URL and parameters"""
    # Create a stable string from params
    param_str = json.dumps(params, sort_keys=True)
    cache_str = f"{url}:{param_str}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def get_cached_result(cache_key, cache_dir, cache_ttl):
    """Retrieve cached result if available and not expired"""
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_entry = json.load(f)
            
            # Check if cache entry has the new structure with timestamp
            if isinstance(cache_entry, dict) and 'timestamp' in cache_entry and 'data' in cache_entry:
                # Check if cache has expired
                age = time.time() - cache_entry['timestamp']
                if age > cache_ttl:
                    logger.info(f"Cache expired (age: {age:.1f}s, TTL: {cache_ttl}s)")
                    return None
                return cache_entry['data']
            else:
                # Old cache format without timestamp - treat as expired
                logger.info("Cache entry has old format without timestamp, treating as expired")
                return None
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
    return None


def save_to_cache(cache_key, data, cache_dir):
    """Save result to cache with timestamp"""
    cache_file = cache_dir / f"{cache_key}.json"
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
