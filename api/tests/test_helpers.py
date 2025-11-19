#!/usr/bin/env python3
"""
Unit tests for helper functions in helpers.py
"""
import unittest
import json
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path to import helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helpers


class TestCacheFunctions(unittest.TestCase):
    """Test cache-related functions"""
    
    def setUp(self):
        """Create temporary cache directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
        self.cache_ttl = 3600  # 1 hour default
    
    def tearDown(self):
        """Clean up temporary cache directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_cache_key_generates_consistent_hash(self):
        """Test that cache key generation is consistent"""
        url = "https://example.com"
        params = {"param1": "value1", "param2": "value2"}
        
        key1 = helpers.get_cache_key(url, params)
        key2 = helpers.get_cache_key(url, params)
        
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)  # MD5 hash length
    
    def test_get_cache_key_different_for_different_inputs(self):
        """Test that different inputs produce different cache keys"""
        url1 = "https://example.com"
        url2 = "https://example.org"
        params = {"param": "value"}
        
        key1 = helpers.get_cache_key(url1, params)
        key2 = helpers.get_cache_key(url2, params)
        
        self.assertNotEqual(key1, key2)
    
    def test_get_cache_key_params_order_independent(self):
        """Test that parameter order doesn't affect cache key"""
        url = "https://example.com"
        params1 = {"a": "1", "b": "2", "c": "3"}
        params2 = {"c": "3", "a": "1", "b": "2"}
        
        key1 = helpers.get_cache_key(url, params1)
        key2 = helpers.get_cache_key(url, params2)
        
        self.assertEqual(key1, key2)
    
    def test_save_to_cache_creates_file(self):
        """Test that save_to_cache creates a cache file"""
        cache_key = "test_key"
        data = {"test": "data"}
        
        helpers.save_to_cache(cache_key, data, self.cache_dir)
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        self.assertTrue(cache_file.exists())
    
    def test_save_to_cache_includes_timestamp(self):
        """Test that saved cache includes timestamp"""
        cache_key = "test_key"
        data = {"test": "data"}
        
        before_time = time.time()
        helpers.save_to_cache(cache_key, data, self.cache_dir)
        after_time = time.time()
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'r') as f:
            cache_entry = json.load(f)
        
        self.assertIn('timestamp', cache_entry)
        self.assertIn('data', cache_entry)
        self.assertGreaterEqual(cache_entry['timestamp'], before_time)
        self.assertLessEqual(cache_entry['timestamp'], after_time)
        self.assertEqual(cache_entry['data'], data)
    
    def test_get_cached_result_returns_none_if_not_exists(self):
        """Test that get_cached_result returns None if cache doesn't exist"""
        result = helpers.get_cached_result("nonexistent_key", self.cache_dir, self.cache_ttl)
        self.assertIsNone(result)
    
    def test_get_cached_result_returns_data_if_valid(self):
        """Test that get_cached_result returns data if cache is valid"""
        cache_key = "test_key"
        data = {"test": "data"}
        
        helpers.save_to_cache(cache_key, data, self.cache_dir)
        result = helpers.get_cached_result(cache_key, self.cache_dir, self.cache_ttl)
        
        self.assertEqual(result, data)
    
    def test_get_cached_result_returns_none_if_expired(self):
        """Test that get_cached_result returns None if cache is expired"""
        cache_key = "test_key"
        data = {"test": "data"}
        
        # Save cache with old timestamp
        cache_file = self.cache_dir / f"{cache_key}.json"
        cache_entry = {
            'timestamp': time.time() - self.cache_ttl - 1,
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_entry, f)
        
        result = helpers.get_cached_result(cache_key, self.cache_dir, self.cache_ttl)
        self.assertIsNone(result)
    
    def test_get_cached_result_handles_old_format(self):
        """Test that get_cached_result treats old cache format as expired"""
        cache_key = "test_key"
        data = {"test": "data"}
        
        # Save cache in old format (without timestamp wrapper)
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        
        result = helpers.get_cached_result(cache_key, self.cache_dir, self.cache_ttl)
        self.assertIsNone(result)
    
    def test_get_cached_result_handles_corrupted_cache(self):
        """Test that get_cached_result handles corrupted cache files"""
        cache_key = "test_key"
        
        # Create corrupted cache file
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            f.write("invalid json{")
        
        result = helpers.get_cached_result(cache_key, self.cache_dir, self.cache_ttl)
        self.assertIsNone(result)


class TestParsingFunctions(unittest.TestCase):
    """Test parameter parsing functions"""
    
    def test_parse_bool_param_with_none_returns_default(self):
        """Test parse_bool_param returns default when value is None"""
        self.assertTrue(helpers.parse_bool_param(None, True))
        self.assertFalse(helpers.parse_bool_param(None, False))
    
    def test_parse_bool_param_with_bool_returns_value(self):
        """Test parse_bool_param returns value when it's already a bool"""
        self.assertTrue(helpers.parse_bool_param(True, False))
        self.assertFalse(helpers.parse_bool_param(False, True))
    
    def test_parse_bool_param_with_string_true_values(self):
        """Test parse_bool_param with string true values"""
        for value in ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']:
            self.assertTrue(helpers.parse_bool_param(value, False))
    
    def test_parse_bool_param_with_string_false_values(self):
        """Test parse_bool_param with string false values"""
        for value in ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO']:
            self.assertFalse(helpers.parse_bool_param(value, True))
    
    def test_parse_int_param_with_none_returns_default(self):
        """Test parse_int_param returns default when value is None"""
        self.assertEqual(helpers.parse_int_param(None, 42), 42)
    
    def test_parse_int_param_with_empty_string_returns_default(self):
        """Test parse_int_param returns default when value is empty string"""
        self.assertEqual(helpers.parse_int_param('', 42), 42)
    
    def test_parse_int_param_with_valid_int_string(self):
        """Test parse_int_param with valid integer string"""
        self.assertEqual(helpers.parse_int_param('123', 0), 123)
        self.assertEqual(helpers.parse_int_param('0', 42), 0)
        self.assertEqual(helpers.parse_int_param('-5', 0), -5)
    
    def test_parse_int_param_with_invalid_string_returns_default(self):
        """Test parse_int_param returns default with invalid string"""
        self.assertEqual(helpers.parse_int_param('abc', 42), 42)
        self.assertEqual(helpers.parse_int_param('12.5', 42), 42)
    
    def test_parse_list_param_with_none_returns_default(self):
        """Test parse_list_param returns default when value is None"""
        self.assertEqual(helpers.parse_list_param(None, 'default'), 'default')
    
    def test_parse_list_param_with_empty_string_returns_default(self):
        """Test parse_list_param returns default when value is empty string"""
        self.assertEqual(helpers.parse_list_param('', 'default'), 'default')
    
    def test_parse_list_param_with_value_returns_value(self):
        """Test parse_list_param returns value when provided"""
        self.assertEqual(helpers.parse_list_param('a,b,c', ''), 'a,b,c')
        self.assertEqual(helpers.parse_list_param('single', ''), 'single')


class TestExtractMetaTags(unittest.TestCase):
    """Test meta tag extraction function"""
    
    def test_extract_meta_tags_with_no_meta_tags(self):
        """Test extract_meta_tags returns None when no meta tags found"""
        html = "<html><head><title>Test</title></head><body></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_meta_tags(soup)
        self.assertIsNone(result)
    
    def test_extract_meta_tags_with_og_tags(self):
        """Test extract_meta_tags extracts Open Graph tags"""
        html = """
        <html>
        <head>
            <meta property="og:title" content="Test Title">
            <meta property="og:description" content="Test Description">
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_meta_tags(soup)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['og_title'], 'Test Title')
        self.assertEqual(result['og_description'], 'Test Description')
        self.assertEqual(result['og_image'], 'https://example.com/image.jpg')
    
    def test_extract_meta_tags_with_twitter_tags(self):
        """Test extract_meta_tags extracts Twitter tags"""
        html = """
        <html>
        <head>
            <meta name="twitter:card" content="summary">
            <meta name="twitter:title" content="Twitter Title">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_meta_tags(soup)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['twitter_card'], 'summary')
        self.assertEqual(result['twitter_title'], 'Twitter Title')
    
    def test_extract_meta_tags_with_mixed_tags(self):
        """Test extract_meta_tags extracts both OG and Twitter tags"""
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <meta name="twitter:card" content="summary">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_meta_tags(soup)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['og_title'], 'OG Title')
        self.assertEqual(result['twitter_card'], 'summary')


class TestExtractArticleContent(unittest.TestCase):
    """Test article content extraction function"""
    
    def test_extract_article_content_with_article_tag(self):
        """Test extract_article_content finds article tag"""
        html = """
        <html>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>Article content</p>
            </article>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_article_content(soup)
        
        self.assertIsNotNone(result)
        self.assertIn('Article Title', result)
        self.assertIn('Article content', result)
    
    def test_extract_article_content_with_main_tag(self):
        """Test extract_article_content finds main tag when no article"""
        html = """
        <html>
        <body>
            <main>
                <h1>Main Title</h1>
                <p>Main content</p>
            </main>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_article_content(soup)
        
        self.assertIsNotNone(result)
        self.assertIn('Main Title', result)
        self.assertIn('Main content', result)
    
    def test_extract_article_content_with_common_class_names(self):
        """Test extract_article_content finds divs with common article classes"""
        html = """
        <html>
        <body>
            <div class="article-content">
                <h1>Content Title</h1>
                <p>Content text</p>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_article_content(soup)
        
        self.assertIsNotNone(result)
        self.assertIn('Content Title', result)
        self.assertIn('Content text', result)
    
    def test_extract_article_content_returns_none_if_not_found(self):
        """Test extract_article_content returns None if no content found"""
        html = """
        <html>
        <body>
            <div class="other">
                <p>Some text</p>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_article_content(soup)
        
        self.assertIsNone(result)
    
    def test_extract_article_content_prefers_article_over_main(self):
        """Test extract_article_content prefers article tag over main"""
        html = """
        <html>
        <body>
            <main>Main content</main>
            <article>Article content</article>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_article_content(soup)
        
        self.assertIn('Article content', result)
        self.assertNotIn('Main content', result)


class TestExtractTextContent(unittest.TestCase):
    """Test text content extraction function"""
    
    def test_extract_text_content_removes_scripts(self):
        """Test extract_text_content removes script tags"""
        html = """
        <html>
        <body>
            <p>Visible text</p>
            <script>console.log('script');</script>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_text_content(soup)
        
        self.assertIn('Visible text', result)
        self.assertNotIn('script', result)
    
    def test_extract_text_content_removes_styles(self):
        """Test extract_text_content removes style tags"""
        html = """
        <html>
        <body>
            <p>Visible text</p>
            <style>body { color: red; }</style>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_text_content(soup)
        
        self.assertIn('Visible text', result)
        self.assertNotIn('color', result)
    
    def test_extract_text_content_removes_nav_header_footer(self):
        """Test extract_text_content removes nav, header, footer"""
        html = """
        <html>
        <body>
            <header>Header content</header>
            <nav>Navigation</nav>
            <p>Main content</p>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_text_content(soup)
        
        self.assertIn('Main content', result)
        self.assertNotIn('Header content', result)
        self.assertNotIn('Navigation', result)
        self.assertNotIn('Footer content', result)
    
    def test_extract_text_content_cleans_multiple_newlines(self):
        """Test extract_text_content cleans up multiple newlines"""
        html = """
        <html>
        <body>
            <p>Line 1</p>
            
            
            <p>Line 2</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_text_content(soup)
        
        # Should not have more than 2 consecutive newlines
        self.assertNotIn('\n\n\n', result)
    
    def test_extract_text_content_returns_none_if_empty(self):
        """Test extract_text_content returns None if no text"""
        html = """
        <html>
        <body>
            <script>console.log('only script');</script>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_text_content(soup)
        
        # Should return None or empty after cleanup
        self.assertTrue(result is None or result.strip() == '')


class TestExtractPublishedTime(unittest.TestCase):
    """Test published time extraction function"""
    
    def test_extract_published_time_from_article_meta(self):
        """Test extract_published_time from article:published_time meta"""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2023-01-15T10:30:00Z">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_published_time(soup)
        
        self.assertEqual(result, '2023-01-15T10:30:00Z')
    
    def test_extract_published_time_from_publication_date_meta(self):
        """Test extract_published_time from publication_date meta"""
        html = """
        <html>
        <head>
            <meta name="publication_date" content="2023-01-15">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_published_time(soup)
        
        self.assertEqual(result, '2023-01-15')
    
    def test_extract_published_time_from_time_tag(self):
        """Test extract_published_time from time tag datetime attribute"""
        html = """
        <html>
        <body>
            <time datetime="2023-01-15T10:30:00Z">January 15, 2023</time>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_published_time(soup)
        
        self.assertEqual(result, '2023-01-15T10:30:00Z')
    
    def test_extract_published_time_returns_none_if_not_found(self):
        """Test extract_published_time returns None if no time found"""
        html = """
        <html>
        <head><title>Test</title></head>
        <body><p>Content</p></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_published_time(soup)
        
        self.assertIsNone(result)
    
    def test_extract_published_time_prefers_article_meta(self):
        """Test extract_published_time prefers article:published_time"""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2023-01-15">
            <meta name="publication_date" content="2023-01-20">
        </head>
        <body>
            <time datetime="2023-01-25">January 25, 2023</time>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = helpers.extract_published_time(soup)
        
        self.assertEqual(result, '2023-01-15')


if __name__ == '__main__':
    unittest.main()
