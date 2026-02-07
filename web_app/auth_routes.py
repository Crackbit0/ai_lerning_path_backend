from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
# Assuming db and login_manager are initialized in __init__.py
from web_app import db, login_manager
from web_app.models import User
from web_app.auth_forms import LoginForm, RegistrationForm
import json
import random
import logging
import jwt
from datetime import datetime, timedelta
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

# Define the blueprint
# If we later move this to an 'auth' subdirectory, the template_folder might change.
bp = Blueprint('auth', __name__, template_folder='templates/auth')


# ============================================================
# JWT TOKEN UTILITIES FOR MOBILE APP
# ============================================================

def generate_jwt_token(user_id, expires_in_days=30):
    """Generate a JWT token for mobile authentication"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=expires_in_days),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_jwt_token(token):
    """Verify a JWT token and return the user_id"""
    try:
        payload = jwt.decode(
            token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require JWT token authentication for API endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        user_id = verify_jwt_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Get the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Pass the user to the route
        return f(user, *args, **kwargs)

    return decorated


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()

    # Handle form submission
    if form.validate_on_submit():
        logger.info(
            f"Registration form validated for email: {form.email.data}")
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)

        # Add registration metadata
        user.registration_source = 'email_password'
        user.last_seen = datetime.utcnow()

        db.session.add(user)
        db.session.commit()
        logger.info(f"User created: {user.email}")

        # Personalized welcome message
        welcome_messages = [
            f"Welcome to the community, {user.username}!",
            f"Your learning journey begins now, {user.username}!",
            f"Congratulations on joining, {user.username}!",
            f"You're all set to start learning, {user.username}!"
        ]
        flash(random.choice(welcome_messages), 'success')

        # Auto-login after registration for seamless experience
        login_user(user)
        logger.info(f"User logged in after registration: {user.email}")
        dashboard_url = url_for('main.dashboard')
        logger.info(f"Redirecting to dashboard: {dashboard_url}")

        # Use render template with meta refresh as fallback
        return render_template('redirect.html', redirect_url=dashboard_url)
    else:
        if form.is_submitted():
            logger.warning(
                f"Registration form validation failed: {form.errors}")

    return render_template('register.html', title='Join the Community', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        logger.info(f"Login form validated for email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.check_password(form.password.data):
            # Helpful error message
            if user is None:
                logger.warning(
                    f"Login failed: No user found for email {form.email.data}")
                flash(
                    'No account found with this email. Would you like to register?', 'warning')
                return redirect(url_for('auth.register', email=form.email.data))
            else:
                logger.warning(
                    f"Login failed: Wrong password for {form.email.data}")
                flash('Incorrect password. Please try again.', 'danger')
                return redirect(url_for('auth.login'))

        # Login successful
        login_user(user, remember=form.remember_me.data)
        logger.info(f"User logged in successfully: {user.email}")

        # Update last seen
        user.last_seen = datetime.utcnow()
        db.session.commit()

        # Personalized welcome back message
        greeting = form.get_greeting()
        motivation = form.get_motivation()
        flash(f"{greeting} {motivation}", 'success')

        # Redirect handling
        next_page = request.args.get('next')
        # Basic security check - default to dashboard if no next page or invalid
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')

        logger.info(f"Redirecting to: {next_page}")

        # Use render template with meta refresh as fallback
        return render_template('redirect.html', redirect_url=next_page)
    else:
        if form.is_submitted():
            logger.warning(f"Login form validation failed: {form.errors}")

    # Pre-fill email if coming from registration suggestion
    if request.args.get('email'):
        form.email.data = request.args.get('email')

    return render_template('login.html', title='Welcome Back', form=form)


@bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()

    # Friendly goodbye messages
    goodbye_messages = [
        f"See you soon, {username}!",
        f"Come back soon, {username}!",
        f"Your learning path will be waiting, {username}!",
        f"Taking a break? We'll be here when you return, {username}!"
    ]

    flash(random.choice(goodbye_messages), 'info')
    return redirect('/')

# This is needed by Flask-Login to load a user from the session


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# AJAX routes for enhanced user experience


@bp.route('/check-username', methods=['POST'])
def check_username():
    """Check if a username is available and suggest alternatives if not"""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()

    if len(username) < 3:
        return jsonify({
            'available': False,
            'message': 'Username must be at least 3 characters long'
        })

    user = User.query.filter_by(username=username).first()
    if user is not None:
        base = username
        suggestions = [
            f"{base}{random.randint(1, 999)}",
            f"awesome_{base}",
            f"{base}_learner"
        ]

        return jsonify({
            'available': False,
            'message': 'This username is already taken',
            'suggestions': suggestions
        })

    return jsonify({
        'available': True,
        'message': 'Username is available!'
    })


# ============================================================
# JSON API ENDPOINTS FOR MOBILE APP
# ============================================================

@bp.route('/api/register', methods=['POST'])
def register_json():
    """JSON API endpoint for mobile app registration"""
    try:
        data = request.get_json(silent=True) or {}

        username = data.get('username', '').strip(
        ) or data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        password2 = data.get('password2', '').strip(
        ) or password  # If not provided, use password

        # Validation
        if not all([username, email, password]):
            return jsonify({'error': 'All fields are required'}), 400

        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400

        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        if password != password2:
            return jsonify({'error': 'Passwords do not match'}), 400

        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        user.registration_source = 'mobile'
        user.last_seen = datetime.utcnow()

        db.session.add(user)
        db.session.commit()

        # Generate JWT token for mobile authentication
        token = generate_jwt_token(user.id)

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'display_name': user.display_name or user.username
            },
            'token': token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/login', methods=['POST'])
def login_json():
    """JSON API endpoint for mobile app login"""
    try:
        data = request.get_json(silent=True) or {}

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        # Update last seen and login count
        user.last_seen = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        db.session.commit()

        # Generate JWT token for mobile authentication
        token = generate_jwt_token(user.id)

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'display_name': user.display_name or user.username
            },
            'token': token
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/logout', methods=['POST'])
@login_required
def logout_json():
    """JSON API endpoint for mobile app logout"""
    try:
        logout_user()
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/user', methods=['GET'])
@login_required
def get_user():
    """Get current user information - JSON endpoint for mobile"""
    try:
        user = current_user
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'display_name': user.display_name or user.username,
                'bio': user.bio or '',
                'created_at': user.date_created.isoformat() if user.date_created else None,
                'login_count': getattr(user, 'login_count', 0),
                'registration_source': user.registration_source or 'web'
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
