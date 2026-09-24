#!/usr/bin/env python3
"""
Unit tests for bearer token authentication in auth.py
"""
import unittest
import json
import sys
import os
from flask import Flask, jsonify

# Add parent directory to path to import auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth


class TestParseTokens(unittest.TestCase):
    """Test the token list parser"""

    def test_none_returns_empty_list(self):
        """Test that None produces no tokens"""
        self.assertEqual(auth.parse_tokens(None), [])

    def test_empty_string_returns_empty_list(self):
        """Test that an empty string produces no tokens"""
        self.assertEqual(auth.parse_tokens(''), [])

    def test_whitespace_only_returns_empty_list(self):
        """Test that a whitespace-only string produces no tokens"""
        self.assertEqual(auth.parse_tokens('   '), [])

    def test_single_token(self):
        """Test that a single value produces one token"""
        self.assertEqual(auth.parse_tokens('secret'), ['secret'])

    def test_strips_surrounding_whitespace(self):
        """Test that surrounding whitespace is removed from each token"""
        self.assertEqual(auth.parse_tokens('  secret  '), ['secret'])

    def test_comma_separated_list(self):
        """Test that a comma-separated string produces several tokens"""
        self.assertEqual(auth.parse_tokens('old, new'), ['old', 'new'])

    def test_skips_empty_entries(self):
        """Test that empty list entries are skipped"""
        self.assertEqual(auth.parse_tokens('a,,b,'), ['a', 'b'])


class AuthTestCase(unittest.TestCase):
    """Base class that builds a Flask app guarded by register_auth"""

    tokens = ['secret']

    def setUp(self):
        """Build a small app with one exempt route and one protected route"""
        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/health')
        def health():
            return jsonify({'status': 'healthy'}), 200

        @app.route('/api/article')
        def article():
            return jsonify({'title': 'ok'}), 200

        auth.register_auth(app, self.tokens)
        self.app = app
        self.client = app.test_client()


class TestExemptPaths(AuthTestCase):
    """Test the paths that never need a token"""

    def test_health_allows_request_without_token(self):
        """Test that /health answers without an Authorization header"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

    def test_health_allows_request_with_wrong_token(self):
        """Test that /health ignores a wrong token instead of rejecting it"""
        response = self.client.get(
            '/health', headers={'Authorization': 'Bearer wrong'}
        )
        self.assertEqual(response.status_code, 200)


class TestMissingToken(AuthTestCase):
    """Test requests that carry no usable credential"""

    def test_missing_header_returns_401(self):
        """Test that a protected route rejects a request with no header"""
        response = self.client.get('/api/article')
        self.assertEqual(response.status_code, 401)

    def test_missing_header_uses_the_error_envelope(self):
        """Test that the 401 body matches the API error format"""
        response = self.client.get('/api/article')

        data = json.loads(response.data)
        self.assertIn('detail', data)
        self.assertIsInstance(data['detail'], list)
        self.assertEqual(data['detail'][0]['type'], 'missing_token')
        self.assertIn('msg', data['detail'][0])

    def test_missing_header_sets_www_authenticate(self):
        """Test that the 401 advertises the Bearer scheme"""
        response = self.client.get('/api/article')
        self.assertEqual(response.headers.get('WWW-Authenticate'), 'Bearer')

    def test_wrong_scheme_returns_invalid_header(self):
        """Test that a non-Bearer scheme is reported as a bad header"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Basic c2VjcmV0'}
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(
            data['detail'][0]['type'], 'invalid_authorization_header'
        )

    def test_scheme_without_value_returns_invalid_header(self):
        """Test that a Bearer header with no token is reported as bad"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer'}
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(
            data['detail'][0]['type'], 'invalid_authorization_header'
        )

    def test_query_parameter_does_not_authenticate(self):
        """Test that a token in the query string is not accepted"""
        response = self.client.get('/api/article?token=secret')

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['detail'][0]['type'], 'missing_token')


class TestWrongToken(AuthTestCase):
    """Test requests that carry a credential that does not match"""

    def test_wrong_token_returns_401(self):
        """Test that a wrong token is rejected"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer wrong'}
        )
        self.assertEqual(response.status_code, 401)

    def test_wrong_token_reports_invalid_token(self):
        """Test that a wrong token is reported as an invalid token"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer wrong'}
        )

        data = json.loads(response.data)
        self.assertEqual(data['detail'][0]['type'], 'invalid_token')

    def test_error_body_never_contains_a_token(self):
        """Test that the rejection body leaks neither token"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer wrong'}
        )

        body = response.data.decode()
        self.assertNotIn('secret', body)
        self.assertNotIn('wrong', body)

    def test_token_prefix_is_rejected(self):
        """Test that a prefix of the real token does not pass"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer secre'}
        )
        self.assertEqual(response.status_code, 401)


class TestValidToken(AuthTestCase):
    """Test requests that carry a matching credential"""

    def test_correct_token_is_accepted(self):
        """Test that the configured token opens a protected route"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer secret'}
        )
        self.assertEqual(response.status_code, 200)

    def test_scheme_match_is_case_insensitive(self):
        """Test that a lowercase bearer scheme is accepted"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'bearer secret'}
        )
        self.assertEqual(response.status_code, 200)

    def test_extra_whitespace_after_scheme_is_accepted(self):
        """Test that extra spaces between scheme and token are tolerated"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer   secret'}
        )
        self.assertEqual(response.status_code, 200)


class TestTokenRotation(AuthTestCase):
    """Test that several tokens can be valid at the same time"""

    tokens = ['old', 'new']

    def test_first_token_is_accepted(self):
        """Test that the first configured token is accepted"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer old'}
        )
        self.assertEqual(response.status_code, 200)

    def test_second_token_is_accepted(self):
        """Test that the second configured token is accepted"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer new'}
        )
        self.assertEqual(response.status_code, 200)

    def test_unlisted_token_is_rejected(self):
        """Test that a token outside the list is rejected"""
        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer other'}
        )
        self.assertEqual(response.status_code, 401)


class TestNoTokenConfigured(AuthTestCase):
    """Test the open mode that keeps existing deployments working"""

    tokens = []

    def test_protected_route_stays_open(self):
        """Test that no configured token leaves the API open"""
        response = self.client.get('/api/article')
        self.assertEqual(response.status_code, 200)

    def test_health_stays_open(self):
        """Test that /health still answers when no token is configured"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)


class TestTokensReadFromConfig(AuthTestCase):
    """Test that the token list can be changed after registration"""

    tokens = []

    def test_setting_the_config_enables_the_check(self):
        """Test that a token added to app config is enforced"""
        self.app.config['API_TOKENS'] = ['later']

        response = self.client.get('/api/article')

        self.assertEqual(response.status_code, 401)

    def test_setting_the_config_accepts_the_new_token(self):
        """Test that a token added to app config is accepted"""
        self.app.config['API_TOKENS'] = ['later']

        response = self.client.get(
            '/api/article', headers={'Authorization': 'Bearer later'}
        )

        self.assertEqual(response.status_code, 200)


class TestCustomExemptPaths(unittest.TestCase):
    """Test that the exempt path list can be changed"""

    def test_a_route_outside_the_exempt_list_is_protected(self):
        """Test that only the listed paths skip the token check"""
        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/health')
        def health():
            return jsonify({'status': 'healthy'}), 200

        auth.register_auth(app, ['secret'], exempt_paths=[])
        client = app.test_client()

        response = client.get('/health')

        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
