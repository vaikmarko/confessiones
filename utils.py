"""
Utility functions for the Sentimental app
"""

def is_anonymous_user(user_id):
    """Check if user_id represents an anonymous user"""
    if not user_id:
        return True
    
    anonymous_identifiers = ['anonymous', 'anonymous_user', '', 'null', 'undefined']
    return user_id in anonymous_identifiers

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_access_code(code):
    """Check if access code is valid"""
    VALID_ACCESS_CODES = {"UNICORN", "SENTI2025"}
    if not code:
        return False
    return code.upper() in VALID_ACCESS_CODES

def is_demo_user(user_id):
    """Check if user is a demo user (exempt from access code)"""
    if not user_id:
        return False
    return user_id.startswith('demo_') 