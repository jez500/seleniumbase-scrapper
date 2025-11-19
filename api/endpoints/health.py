#!/usr/bin/env python3
"""
Health check endpoint for SeleniumBase API
"""
from flask import jsonify


def register_routes(app):
    """Register health check routes with the Flask app"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'seleniumbase-api'
        }), 200
