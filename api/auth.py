#!/usr/bin/env python3
"""
Bearer token authentication for the SeleniumBase API server

The API is open when no token is configured. Setting API_TOKEN turns the
check on. Set several tokens, separated by commas, to rotate a token without
downtime.
"""
from flask import request, jsonify
import hmac
import logging

logger = logging.getLogger(__name__)

# Paths that never need a token. The Kubernetes startup and liveness probes
# call /health, so it must stay open.
DEFAULT_EXEMPT_PATHS = ('/health',)

# Flask config key that holds the list of valid tokens
TOKENS_CONFIG_KEY = 'API_TOKENS'


def parse_tokens(raw):
    """Return the list of tokens from a comma-separated string

    Args:
        raw (str): the raw API_TOKEN value, or None.

    Returns:
        list: one entry per non-empty token, with whitespace removed.
    """
    if not raw:
        return []
    return [token.strip() for token in raw.split(',') if token.strip()]


def _reject(error_type, message):
    """Build a 401 response in the error format the API already uses"""
    response = jsonify({
        'detail': [
            {
                'type': error_type,
                'msg': message
            }
        ]
    })
    response.status_code = 401
    response.headers['WWW-Authenticate'] = 'Bearer'
    return response


def _token_from_header(header):
    """Return the token from an Authorization header value

    Returns None when the header does not read "Bearer <token>".
    """
    parts = header.split(None, 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != 'bearer':
        return None
    token = parts[1].strip()
    if not token:
        return None
    return token


def _matches_any(presented, tokens):
    """Compare the presented token against every valid token

    The comparison uses hmac.compare_digest, so a wrong token cannot leak its
    correct prefix through response timing. Every token is compared, so the
    position of a match in the list does not change the work done either.
    """
    presented_bytes = presented.encode('utf-8')
    matched = False
    for token in tokens:
        if hmac.compare_digest(presented_bytes, token.encode('utf-8')):
            matched = True
    return matched


def register_auth(app, tokens, exempt_paths=DEFAULT_EXEMPT_PATHS):
    """Install the bearer token check on the Flask app

    The check runs before every request. It reads the token list from
    app.config[TOKENS_CONFIG_KEY], so a caller can change the list later.
    An empty list leaves the API open.

    Args:
        app: the Flask application.
        tokens (list): the valid tokens.
        exempt_paths (iterable): paths that never need a token.
    """
    app.config[TOKENS_CONFIG_KEY] = list(tokens)
    exempt = set(exempt_paths)

    if not app.config[TOKENS_CONFIG_KEY]:
        logger.warning(
            "API_TOKEN is not set, so the API accepts every request. "
            "Set API_TOKEN to require a bearer token."
        )
    else:
        logger.info(
            f"Bearer token authentication is on with "
            f"{len(app.config[TOKENS_CONFIG_KEY])} valid token(s). "
            f"Open paths: {', '.join(sorted(exempt)) or 'none'}"
        )

    @app.before_request
    def require_bearer_token():
        """Reject a request that carries no valid bearer token"""
        valid_tokens = app.config.get(TOKENS_CONFIG_KEY) or []
        if not valid_tokens:
            return None
        if request.path in exempt:
            return None

        header = request.headers.get('Authorization')
        if not header:
            logger.warning(
                f"Rejected {request.method} {request.path} "
                f"from {request.remote_addr}: no Authorization header"
            )
            return _reject(
                'missing_token',
                'Missing Authorization header. '
                'Send: Authorization: Bearer <token>'
            )

        presented = _token_from_header(header)
        if not presented:
            logger.warning(
                f"Rejected {request.method} {request.path} "
                f"from {request.remote_addr}: malformed Authorization header"
            )
            return _reject(
                'invalid_authorization_header',
                'The Authorization header must read: Bearer <token>'
            )

        if not _matches_any(presented, valid_tokens):
            logger.warning(
                f"Rejected {request.method} {request.path} "
                f"from {request.remote_addr}: invalid token"
            )
            return _reject('invalid_token', 'The bearer token is not valid')

        return None
