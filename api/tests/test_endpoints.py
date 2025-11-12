#!/usr/bin/env python3
"""
Integration/Feature tests for API endpoints in server.py
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add parent directory to path to import server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server


class TestHealthEndpoint(unittest.TestCase):
    """Test /health endpoint"""
    
    def setUp(self):
        """Set up test client"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
    
    def test_health_endpoint_returns_200(self):
        """Test that /health endpoint returns 200 status"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
    
    def test_health_endpoint_returns_json(self):
        """Test that /health endpoint returns JSON"""
        response = self.client.get('/health')
        self.assertEqual(response.content_type, 'application/json')
    
    def test_health_endpoint_contains_status(self):
        """Test that /health endpoint contains status field"""
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_health_endpoint_contains_service_name(self):
        """Test that /health endpoint contains service field"""
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        self.assertIn('service', data)
        self.assertEqual(data['service'], 'seleniumbase-api')


class TestRootEndpoint(unittest.TestCase):
    """Test / (root) endpoint"""
    
    def setUp(self):
        """Set up test client"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
    
    def test_root_endpoint_returns_200(self):
        """Test that / endpoint returns 200 status"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_root_endpoint_returns_json(self):
        """Test that / endpoint returns JSON"""
        response = self.client.get('/')
        self.assertEqual(response.content_type, 'application/json')
    
    def test_root_endpoint_contains_service_info(self):
        """Test that / endpoint contains service information"""
        response = self.client.get('/')
        data = json.loads(response.data)
        
        self.assertIn('service', data)
        self.assertIn('version', data)
        self.assertEqual(data['service'], 'SeleniumBase API')
    
    def test_root_endpoint_contains_endpoints_documentation(self):
        """Test that / endpoint contains endpoints documentation"""
        response = self.client.get('/')
        data = json.loads(response.data)
        
        self.assertIn('endpoints', data)
        self.assertIn('/api/article', data['endpoints'])
        self.assertIn('/health', data['endpoints'])
    
    def test_root_endpoint_article_docs_complete(self):
        """Test that /api/article documentation is complete"""
        response = self.client.get('/')
        data = json.loads(response.data)
        
        article_docs = data['endpoints']['/api/article']
        self.assertIn('method', article_docs)
        self.assertIn('description', article_docs)
        self.assertIn('parameters', article_docs)
        self.assertIn('example', article_docs)


class TestArticleEndpointBasics(unittest.TestCase):
    """Test basic functionality of /api/article endpoint"""
    
    def setUp(self):
        """Set up test client and temp directories"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        
        # Create temporary directories
        self.temp_cache_dir = tempfile.mkdtemp()
        self.temp_screenshots_dir = tempfile.mkdtemp()
        self.temp_user_scripts_dir = tempfile.mkdtemp()
        
        # Store original directories
        self.original_cache_dir = server.CACHE_DIR
        self.original_screenshots_dir = server.SCREENSHOTS_DIR
        self.original_user_scripts_dir = server.USER_SCRIPTS_DIR
        
        # Replace with temp directories
        server.CACHE_DIR = Path(self.temp_cache_dir)
        server.SCREENSHOTS_DIR = Path(self.temp_screenshots_dir)
        server.USER_SCRIPTS_DIR = Path(self.temp_user_scripts_dir)
    
    def tearDown(self):
        """Clean up temp directories"""
        shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        shutil.rmtree(self.temp_screenshots_dir, ignore_errors=True)
        shutil.rmtree(self.temp_user_scripts_dir, ignore_errors=True)
        
        # Restore original directories
        server.CACHE_DIR = self.original_cache_dir
        server.SCREENSHOTS_DIR = self.original_screenshots_dir
        server.USER_SCRIPTS_DIR = self.original_user_scripts_dir
    
    def test_article_endpoint_requires_url(self):
        """Test that /api/article returns error without URL parameter"""
        response = self.client.get('/api/article')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('detail', data)
        self.assertEqual(data['detail'][0]['type'], 'missing_parameter')
    
    def test_article_endpoint_error_format(self):
        """Test that error responses follow the correct format"""
        response = self.client.get('/api/article')
        
        data = json.loads(response.data)
        self.assertIn('detail', data)
        self.assertIsInstance(data['detail'], list)
        self.assertIn('type', data['detail'][0])
        self.assertIn('msg', data['detail'][0])
    
    @patch('server.Driver')
    def test_article_endpoint_with_url(self, mock_driver_class):
        """Test that /api/article works with URL parameter"""
        # Mock the Driver
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><head><title>Test</title></head><body><p>Content</p></body></html>'
        
        response = self.client.get('/api/article?url=https://example.com')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('title', data)
        self.assertIn('content', data)
    
    @patch('server.Driver')
    def test_article_endpoint_returns_all_required_fields(self, mock_driver_class):
        """Test that /api/article returns all required fields"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com/article'
        mock_driver.page_source = '''
        <html lang="en">
        <head>
            <title>Test Article</title>
            <meta name="description" content="Test description">
            <meta name="author" content="Test Author">
        </head>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>Article content here</p>
            </article>
        </body>
        </html>
        '''
        
        response = self.client.get('/api/article?url=https://example.com/article')
        data = json.loads(response.data)
        
        # Check all required fields
        required_fields = [
            'id', 'url', 'domain', 'title', 'byline', 'excerpt',
            'siteName', 'content', 'textContent', 'length', 'lang',
            'dir', 'publishedTime', 'fullContent', 'date', 'query',
            'meta', 'resultUri', 'screenshotUri'
        ]
        
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
    
    @patch('server.Driver')
    def test_article_endpoint_driver_called_correctly(self, mock_driver_class):
        """Test that Driver is instantiated with correct parameters"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        self.client.get('/api/article?url=https://example.com')
        
        # Verify Driver was called
        mock_driver_class.assert_called_once()
        call_kwargs = mock_driver_class.call_args[1]
        
        self.assertEqual(call_kwargs['browser'], 'chrome')
        self.assertTrue(call_kwargs['headless'])
        self.assertTrue(call_kwargs['uc'])
    
    @patch('server.Driver')
    def test_article_endpoint_driver_quit_called(self, mock_driver_class):
        """Test that Driver.quit() is always called"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        self.client.get('/api/article?url=https://example.com')
        
        # Verify quit was called
        mock_driver.quit.assert_called_once()
    
    @patch('server.Driver')
    def test_article_endpoint_handles_driver_exception(self, mock_driver_class):
        """Test that endpoint handles exceptions from Driver"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.get.side_effect = Exception("Connection error")
        
        response = self.client.get('/api/article?url=https://example.com')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('detail', data)
        self.assertEqual(data['detail'][0]['type'], 'fetch_error')


class TestArticleEndpointParameters(unittest.TestCase):
    """Test parameter handling in /api/article endpoint"""
    
    def setUp(self):
        """Set up test client and temp directories"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        
        self.temp_cache_dir = tempfile.mkdtemp()
        self.temp_screenshots_dir = tempfile.mkdtemp()
        self.temp_user_scripts_dir = tempfile.mkdtemp()
        
        self.original_cache_dir = server.CACHE_DIR
        self.original_screenshots_dir = server.SCREENSHOTS_DIR
        self.original_user_scripts_dir = server.USER_SCRIPTS_DIR
        
        server.CACHE_DIR = Path(self.temp_cache_dir)
        server.SCREENSHOTS_DIR = Path(self.temp_screenshots_dir)
        server.USER_SCRIPTS_DIR = Path(self.temp_user_scripts_dir)
    
    def tearDown(self):
        """Clean up temp directories"""
        shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        shutil.rmtree(self.temp_screenshots_dir, ignore_errors=True)
        shutil.rmtree(self.temp_user_scripts_dir, ignore_errors=True)
        
        server.CACHE_DIR = self.original_cache_dir
        server.SCREENSHOTS_DIR = self.original_screenshots_dir
        server.USER_SCRIPTS_DIR = self.original_user_scripts_dir
    
    @patch('server.Driver')
    def test_article_endpoint_full_content_parameter(self, mock_driver_class):
        """Test full-content parameter includes full HTML"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Full HTML content</body></html>'
        
        # Without full-content
        response = self.client.get('/api/article?url=https://example.com')
        data = json.loads(response.data)
        self.assertIsNone(data['fullContent'])
        
        # With full-content
        response = self.client.get('/api/article?url=https://example.com&full-content=true')
        data = json.loads(response.data)
        self.assertIsNotNone(data['fullContent'])
        self.assertIn('Full HTML content', data['fullContent'])
    
    @patch('server.Driver')
    def test_article_endpoint_viewport_parameters(self, mock_driver_class):
        """Test viewport-width and viewport-height parameters"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com&viewport-width=1024&viewport-height=768')
        
        self.assertEqual(response.status_code, 200)
        mock_driver.set_window_size.assert_called_once_with(1024, 768)
    
    @patch('server.Driver')
    def test_article_endpoint_timeout_parameter(self, mock_driver_class):
        """Test timeout parameter"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com&timeout=30000')
        
        self.assertEqual(response.status_code, 200)
        mock_driver.set_page_load_timeout.assert_called_once_with(30.0)
    
    @patch('server.Driver')
    @patch('time.sleep')
    def test_article_endpoint_sleep_parameter(self, mock_sleep, mock_driver_class):
        """Test sleep parameter"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com&sleep=2000')
        
        self.assertEqual(response.status_code, 200)
        # Check that sleep was called with 2.0 seconds
        mock_sleep.assert_called()
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertIn(2.0, sleep_calls)
    
    @patch('server.Driver')
    def test_article_endpoint_scroll_down_parameter(self, mock_driver_class):
        """Test scroll-down parameter"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com&scroll-down=500')
        
        self.assertEqual(response.status_code, 200)
        # Check that execute_script was called with scroll command
        mock_driver.execute_script.assert_called()
        script_calls = [str(call) for call in mock_driver.execute_script.call_args_list]
        self.assertTrue(any('scrollBy' in str(call) for call in script_calls))
    
    @patch('server.Driver')
    def test_article_endpoint_user_scripts_parameter(self, mock_driver_class):
        """Test user-scripts parameter"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        # Create a test user script
        script_path = server.USER_SCRIPTS_DIR / 'test-script.js'
        with open(script_path, 'w') as f:
            f.write('console.log("test");')
        
        response = self.client.get('/api/article?url=https://example.com&user-scripts=test-script.js')
        
        self.assertEqual(response.status_code, 200)
        # Verify execute_script was called with user script
        mock_driver.execute_script.assert_called()
    
    @patch('server.Driver')
    def test_article_endpoint_incognito_parameter(self, mock_driver_class):
        """Test incognito parameter"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com&incognito=false')
        
        self.assertEqual(response.status_code, 200)
        # Check that Driver was called with incognito=False
        call_kwargs = mock_driver_class.call_args[1]
        self.assertFalse(call_kwargs['incognito'])


class TestArticleEndpointCaching(unittest.TestCase):
    """Test caching functionality in /api/article endpoint"""
    
    def setUp(self):
        """Set up test client and temp directories"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        
        self.temp_cache_dir = tempfile.mkdtemp()
        self.temp_screenshots_dir = tempfile.mkdtemp()
        self.temp_user_scripts_dir = tempfile.mkdtemp()
        
        self.original_cache_dir = server.CACHE_DIR
        self.original_screenshots_dir = server.SCREENSHOTS_DIR
        self.original_user_scripts_dir = server.USER_SCRIPTS_DIR
        
        server.CACHE_DIR = Path(self.temp_cache_dir)
        server.SCREENSHOTS_DIR = Path(self.temp_screenshots_dir)
        server.USER_SCRIPTS_DIR = Path(self.temp_user_scripts_dir)
    
    def tearDown(self):
        """Clean up temp directories"""
        shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        shutil.rmtree(self.temp_screenshots_dir, ignore_errors=True)
        shutil.rmtree(self.temp_user_scripts_dir, ignore_errors=True)
        
        server.CACHE_DIR = self.original_cache_dir
        server.SCREENSHOTS_DIR = self.original_screenshots_dir
        server.USER_SCRIPTS_DIR = self.original_user_scripts_dir
    
    @patch('server.Driver')
    def test_article_endpoint_saves_to_cache(self, mock_driver_class):
        """Test that results are saved to cache"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com')
        
        self.assertEqual(response.status_code, 200)
        
        # Check that cache file was created
        cache_files = list(server.CACHE_DIR.glob('*.json'))
        self.assertGreater(len(cache_files), 0)
    
    @patch('server.Driver')
    def test_article_endpoint_uses_cache_when_enabled(self, mock_driver_class):
        """Test that cached results are used when cache=true"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        # First request - creates cache
        response1 = self.client.get('/api/article?url=https://example.com')
        self.assertEqual(response1.status_code, 200)
        
        # Reset mock to verify it's not called again
        mock_driver_class.reset_mock()
        
        # Second request with cache=true
        response2 = self.client.get('/api/article?url=https://example.com&cache=true')
        self.assertEqual(response2.status_code, 200)
        
        # Verify Driver was NOT instantiated again (cache was used)
        mock_driver_class.assert_not_called()
    
    @patch('server.Driver')
    def test_article_endpoint_ignores_cache_by_default(self, mock_driver_class):
        """Test that cache is not used by default"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        # First request - creates cache
        response1 = self.client.get('/api/article?url=https://example.com')
        self.assertEqual(response1.status_code, 200)
        
        # Reset mock
        mock_driver_class.reset_mock()
        
        # Second request without cache parameter
        response2 = self.client.get('/api/article?url=https://example.com')
        self.assertEqual(response2.status_code, 200)
        
        # Verify Driver WAS instantiated again (cache was not used)
        mock_driver_class.assert_called()


class TestArticleEndpointScreenshot(unittest.TestCase):
    """Test screenshot functionality in /api/article endpoint"""
    
    def setUp(self):
        """Set up test client and temp directories"""
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        
        self.temp_cache_dir = tempfile.mkdtemp()
        self.temp_screenshots_dir = tempfile.mkdtemp()
        self.temp_user_scripts_dir = tempfile.mkdtemp()
        
        self.original_cache_dir = server.CACHE_DIR
        self.original_screenshots_dir = server.SCREENSHOTS_DIR
        self.original_user_scripts_dir = server.USER_SCRIPTS_DIR
        
        server.CACHE_DIR = Path(self.temp_cache_dir)
        server.SCREENSHOTS_DIR = Path(self.temp_screenshots_dir)
        server.USER_SCRIPTS_DIR = Path(self.temp_user_scripts_dir)
    
    def tearDown(self):
        """Clean up temp directories"""
        shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        shutil.rmtree(self.temp_screenshots_dir, ignore_errors=True)
        shutil.rmtree(self.temp_user_scripts_dir, ignore_errors=True)
        
        server.CACHE_DIR = self.original_cache_dir
        server.SCREENSHOTS_DIR = self.original_screenshots_dir
        server.USER_SCRIPTS_DIR = self.original_user_scripts_dir
    
    @patch('server.Driver')
    def test_article_endpoint_screenshot_parameter_false(self, mock_driver_class):
        """Test that screenshot is None when screenshot=false"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        
        response = self.client.get('/api/article?url=https://example.com')
        data = json.loads(response.data)
        
        self.assertIsNone(data['screenshotUri'])
        mock_driver.save_screenshot.assert_not_called()
    
    @patch('server.Driver')
    def test_article_endpoint_screenshot_parameter_true(self, mock_driver_class):
        """Test that screenshot is taken when screenshot=true"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.current_url = 'https://example.com'
        mock_driver.page_source = '<html><body>Test</body></html>'
        mock_driver.save_screenshot.return_value = True
        
        response = self.client.get('/api/article?url=https://example.com&screenshot=true')
        data = json.loads(response.data)
        
        self.assertIsNotNone(data['screenshotUri'])
        self.assertTrue(data['screenshotUri'].startswith('file://screenshots/'))
        mock_driver.save_screenshot.assert_called_once()


if __name__ == '__main__':
    unittest.main()
