"""
ANVIQO PHASE 1 SECURITY HARDENING
==================================

Secure wrapper for anviqo_api.py endpoints:
- /api/ask → requires authentication + authorization
- /api/pci → requires authentication
- /api/pci/live → requires authentication

Phase 1 Goals:
1. Protect critical endpoints from unauthenticated access
2. Preserve read-only query behavior (no silent writes)
3. Require explicit authorized mutations for inventory changes
4. Implement secure session cookies and CSRF protection
5. Add audit trail support for all mutations
6. Field reports remain PENDING until human verification

V1.0 - 2026-09-09
"""

from functools import wraps
from flask import request, jsonify, session, make_response
from datetime import datetime, timedelta
import os
import uuid
import logging

# ============================================================
# CONFIGURATION
# ============================================================

PRODUCTION = os.getenv('FLASK_ENV', 'development') == 'production'

# Session cookie security
SESSION_COOKIE_SECURE = PRODUCTION  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_COOKIE_LIFETIME = 3600  # 1 hour

# Request limits
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB

# Logging
logger = logging.getLogger(__name__)

# ============================================================
# AUTHENTICATION DECORATOR
# ============================================================

def login_required(f):
    """
    Decorator to protect endpoints with authentication.
    
    Checks session for authenticated user.
    Returns 401 if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'status': 401
            }), 401
        
        # Attach request context
        request.user_id = session.get('user_id')
        request.username = session.get('username')
        request.request_id = str(uuid.uuid4())
        request.timestamp = datetime.utcnow().isoformat()
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================
# INVENTORY MUTATION AUTHORIZATION
# ============================================================

def inventory_mutation_authorized(f):
    """
    Decorator for inventory mutation endpoints.
    
    Requires:
    - Authentication (via @login_required)
    - User authorization level for inventory mutations
    - Request ID for audit trail
    
    Preserves request context for audit logging.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Must already be authenticated (see decorator order)
        if 'user_id' not in session:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'status': 401
            }), 401
        
        # Check authorization level
        user_role = session.get('role', 'user')
        
        # Allowed roles for inventory mutations
        authorized_roles = ['technician', 'engineer', 'admin']
        
        if user_role not in authorized_roles:
            return jsonify({
                'error': 'Forbidden',
                'message': f'Inventory mutations require authorized role. Current: {user_role}',
                'status': 403
            }), 403
        
        # Attach inventory mutation context
        request.mutation_authorized = True
        request.actor = session.get('username', 'unknown')
        request.actor_id = session.get('user_id')
        request.actor_role = user_role
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================
# CSRF PROTECTION
# ============================================================

def csrf_protect(f):
    """
    CSRF protection for unsafe methods (POST, PUT, DELETE).
    
    Checks CSRF token in request headers or form data.
    Validates against session CSRF token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = (
                request.form.get('csrf_token') or
                request.headers.get('X-CSRF-Token')
            )
            
            session_token = session.get('csrf_token')
            
            if not token or token != session_token:
                return jsonify({
                    'error': 'CSRF validation failed',
                    'message': 'Invalid or missing CSRF token',
                    'status': 403
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================
# SECURE SESSION SETUP
# ============================================================

def configure_secure_session(app):
    """
    Configure Flask app with secure session settings.
    
    Phase 1 security:
    - HttpOnly cookies prevent XSS access
    - Secure flag forces HTTPS in production
    - SameSite=Lax prevents CSRF
    - Short lifetime reduces exposure
    """
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_COOKIE_LIFETIME)
    
    # Additional security headers
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if PRODUCTION:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    logger.info('Secure session configuration applied')


# ============================================================
# REQUEST VALIDATION
# ============================================================

def validate_request_size(max_size=MAX_UPLOAD_SIZE):
    """Validate request payload size."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            
            if content_length and content_length > max_size:
                return jsonify({
                    'error': 'Request too large',
                    'message': f'Request exceeds {max_size} bytes',
                    'status': 413
                }), 413
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# SAFE ERROR RESPONSES
# ============================================================

def safe_error_response(status_code, message, internal_error=None):
    """
    Generate safe error response without leaking internals.
    
    Public message is generic; internal error is logged only.
    """
    
    # Log internal error for debugging (not returned to client)
    if internal_error:
        logger.error(f"Internal error: {internal_error}")
    
    # Public message is generic
    public_messages = {
        400: 'Invalid request',
        401: 'Authentication required',
        403: 'Access denied',
        404: 'Not found',
        409: 'Conflict',
        413: 'Request too large',
        500: 'Internal server error'
    }
    
    return jsonify({
        'error': public_messages.get(status_code, 'Error'),
        'message': message,
        'status': status_code
    }), status_code


# ============================================================
# INVENTORY MUTATION CONTEXT
# ============================================================

class InventoryMutationContext:
    """Context for inventory mutations with audit trail support."""
    
    def __init__(self, request_obj, actor, actor_id, action, tag, quantity):
        self.request_id = getattr(request_obj, 'request_id', str(uuid.uuid4()))
        self.timestamp = datetime.utcnow().isoformat()
        self.actor = actor
        self.actor_id = actor_id
        self.action = action  # ADD, USE, etc.
        self.tag = tag
        self.quantity = quantity
        self.before = None
        self.after = None
        self.success = False
        self.error = None
    
    def to_audit_record(self):
        """Convert to audit trail record."""
        return {
            'request_id': self.request_id,
            'timestamp': self.timestamp,
            'actor': self.actor,
            'actor_id': self.actor_id,
            'action': self.action,
            'tag': self.tag,
            'quantity': self.quantity,
            'before': self.before,
            'after': self.after,
            'success': self.success,
            'error': self.error
        }


# ============================================================
# FIELD REPORT SECURITY
# ============================================================

def field_report_pending_only(parsed_report):
    """
    Ensure field reports are marked PENDING_VERIFICATION.
    
    Parsed field reports must NOT automatically mutate inventory.
    Only explicit authorized mutations may change inventory.
    """
    
    if 'spare_used' in parsed_report or 'spare_received' in parsed_report:
        parsed_report['verification_status'] = 'PENDING_VERIFICATION'
        parsed_report['verified'] = False
        parsed_report['requires_human_verification'] = True
    
    return parsed_report


# ============================================================
# TEST HELPERS
# ============================================================

def create_test_session(app, user_id='test_user', username='technician', role='technician'):
    """Create an authenticated test session."""
    with app.test_request_context():
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = role
        session['csrf_token'] = str(uuid.uuid4())
    
    return {
        'user_id': user_id,
        'username': username,
        'role': role,
        'csrf_token': session.get('csrf_token')
    }
