#!/usr/bin/env python3
"""
Root endpoint for SeleniumBase API
"""
from flask import jsonify


def register_routes(app):
    """Register root routes with the Flask app"""
    
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
