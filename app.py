import os
import json
import logging
import requests
import hashlib
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import query as firestore_query
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load secrets from Google Cloud Secret Manager (for production)
def load_secret(secret_name):
    """Load a secret from Google Cloud Secret Manager or fall back to environment variable."""
    # First try environment variable (local development with .env)
    env_value = os.getenv(secret_name.upper().replace('-', '_'))
    if env_value:
        return env_value
    
    # Try Google Cloud Secret Manager (production)
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'confessiones-c6ca5')
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        secret_value = response.payload.data.decode('UTF-8')
        logger.info(f"Loaded secret '{secret_name}' from Secret Manager")
        return secret_value
    except Exception as e:
        logger.warning(f"Could not load secret '{secret_name}' from Secret Manager: {e}")
        return None

# Load secrets (try Secret Manager first, fall back to environment variables)
if not os.getenv('OPENAI_API_KEY'):
    openai_key = load_secret('openai-api-key')
    if openai_key:
        os.environ['OPENAI_API_KEY'] = openai_key

if not os.getenv('STRIPE_SECRET_KEY'):
    stripe_key = load_secret('stripe-secret-key')
    if stripe_key:
        os.environ['STRIPE_SECRET_KEY'] = stripe_key

if not os.getenv('STRIPE_PUBLISHABLE_KEY'):
    stripe_pub_key = load_secret('stripe-publishable-key')
    if stripe_pub_key:
        os.environ['STRIPE_PUBLISHABLE_KEY'] = stripe_pub_key

if not os.getenv('STRIPE_PRICE_ID_UNLIMITED'):
    stripe_price = load_secret('stripe-price-id-unlimited')
    if stripe_price:
        os.environ['STRIPE_PRICE_ID_UNLIMITED'] = stripe_price

if not os.getenv('FIREBASE_API_KEY'):
    firebase_key = load_secret('firebase-api-key')
    if firebase_key:
        os.environ['FIREBASE_API_KEY'] = firebase_key

if not os.getenv('STRIPE_PRICE_ID_ANNUAL'):
    stripe_annual = load_secret('stripe-price-id-annual')
    if stripe_annual:
        os.environ['STRIPE_PRICE_ID_ANNUAL'] = stripe_annual

if not os.getenv('SENDGRID_API_KEY'):
    sendgrid_key = load_secret('sendgrid-api-key')
    if sendgrid_key:
        os.environ['SENDGRID_API_KEY'] = sendgrid_key

app = Flask(__name__)
CORS(app)

# Initialize SendGrid
sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
if sendgrid_api_key:
    sendgrid_client = SendGridAPIClient(sendgrid_api_key)
    logger.info("SendGrid API configured")
else:
    sendgrid_client = None
    logger.warning("SendGrid API key not found - emails will not be sent")

# ============================================================================
# EMAIL TEMPLATES & FUNCTIONS
# ============================================================================

# Base email template with consistent branding
EMAIL_BASE_TEMPLATE = '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 28px;">✝️ My Confessions</h1>
        <p style="margin: 10px 0 0; opacity: 0.9;">Biblical Guidance for Your Spiritual Journey</p>
    </div>
    
    <div style="padding: 30px; background: white;">
        {content}
    </div>
    
    <div style="background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 12px;">
        <p style="margin: 0;">
            Need help? Contact us at <a href="mailto:support@myconfessions.org" style="color: #2563eb;">support@myconfessions.org</a>
        </p>
        <p style="margin: 10px 0 0;">
            © 2025 My Confessions. All rights reserved.
        </p>
    </div>
</div>
'''

def send_email(to_email, subject, html_content):
    """Generic email sender using SendGrid"""
    if not sendgrid_client:
        logger.warning(f"Cannot send email to {to_email} - SendGrid not configured")
        return False
    
    try:
        message = Mail(
            from_email='support@myconfessions.org',
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        response = sendgrid_client.send(message)
        logger.info(f"Email sent to {to_email}, subject: {subject}, status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_welcome_email(email, name):
    """Send welcome email to new user"""
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Welcome, {name or 'Child of God'}! 🙏</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Thank you for joining My Confessions. We're honored to walk alongside you on your spiritual journey.
        </p>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                "If we confess our sins, He is faithful and just to forgive us our sins 
                and to cleanse us from all unrighteousness."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 5px 0 0; text-align: right;">
                — 1 John 1:9
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">What You Can Do:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li>Have 24/7 Scripture-based spiritual conversations</li>
            <li>Create beautiful prayers from your reflections</li>
            <li>Save your spiritual journey (with Premium)</li>
            <li>Share prayers anonymously to help others (with Premium)</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Start Your Spiritual Journey
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            May God's peace be with you,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, 'Welcome to My Confessions - Your Spiritual Journey Begins', html)

def send_password_reset_email(email, reset_token):
    """Send password reset email"""
    reset_url = f"https://myconfessions.org/reset-password?token={reset_token}"
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Password Reset Request 🔑</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            We received a request to reset your password for your My Confessions account.
        </p>
        
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
            <p style="color: #92400e; margin: 0; font-weight: bold;">
                ⚠️ If you did not request this, please ignore this email.
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Reset Your Password
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; text-align: center;">
            This link will expire in 1 hour for your security.
        </p>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Praying for your peace,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, 'Reset Your Password - My Confessions', html)

def send_subscription_activated_email(email, name, plan_type, amount):
    """Send email when subscription is activated"""
    plan_display = "Annual ($39.99/year)" if plan_type == 'annual' else "Monthly ($4.99/month)"
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Welcome to Premium! 💎</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Beloved Child of God'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            Your Premium membership has been activated! Thank you for supporting our ministry.
        </p>
        
        <div style="background: #dcfce7; border: 2px solid #16a34a; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h3 style="color: #166534; margin: 0 0 10px;">✅ Subscription Active</h3>
            <p style="color: #166534; margin: 0; font-size: 18px; font-weight: bold;">
                {plan_display}
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">Your Premium Benefits:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li><strong>Unlimited Biblical guidance</strong> - 24/7 access to spiritual conversations</li>
            <li><strong>Community prayers</strong> - Read and share prayers with fellow believers</li>
            <li><strong>Journey saved</strong> - All your conversations are preserved</li>
            <li><strong>Priority support</strong> - We're here to help you</li>
        </ul>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                "For where two or three gather in my name, there am I with them."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 5px 0 0; text-align: right;">
                — Matthew 18:20
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Continue Your Journey
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Thank you for your partnership in spreading God's word through technology.<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, '✅ Your Premium Membership is Active!', html)

def send_subscription_cancelled_email(email, name):
    """Send email when subscription is cancelled"""
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Your Subscription Has Been Cancelled</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Beloved Friend'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            We're sorry to see you go. Your Premium membership has been cancelled and will remain active until the end of your current billing period.
        </p>
        
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
            <p style="color: #92400e; margin: 0;">
                <strong>What happens now:</strong><br>
                • You can still use Premium features until your subscription ends<br>
                • After that, you'll have access to our Free tier (20 conversations/month)<br>
                • Your data will be preserved
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">We'd Love to Have You Back</h3>
        <p style="color: #374151; line-height: 1.6;">
            You can reactivate your subscription anytime. We're always here to support your spiritual growth.
        </p>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                "The Lord is close to the brokenhearted and saves those who are crushed in spirit."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 5px 0 0; text-align: right;">
                — Psalm 34:18
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Reactivate Membership
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            May God's blessings be with you always,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, 'Your Subscription Has Been Cancelled', html)

def send_payment_failed_email(email, name):
    """Send email when subscription payment fails"""
    content = f'''
        <h2 style="color: #dc2626; margin-top: 0;">Payment Issue - Action Required ⚠️</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Valued Member'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            We were unable to process your recent payment for My Confessions Premium membership.
        </p>
        
        <div style="background: #fee2e2; border: 2px solid #dc2626; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #dc2626; margin: 0 0 10px;">⚠️ Payment Failed</h3>
            <p style="color: #991b1b; margin: 0;">
                Your subscription will be cancelled if we cannot process payment within 7 days.
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">Please Update Your Payment Method:</h3>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org/app" 
               style="background: #dc2626; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Update Payment Method
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">
            If you have questions, please contact us at support@myconfessions.org
        </p>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            In His service,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, '⚠️ Payment Failed - Update Your Payment Method', html)

def send_spiritual_followup_email(email, name, days_since_last, session_id=None):
    """Send follow-up email to encourage continued spiritual growth"""
    
    # Check preferences
    if session_id and not check_email_preferences(session_id, 'marketing'):
        logger.info(f"Skipping follow-up email for {email} - user opted out of marketing emails")
        return False
    
    # Different messages based on inactivity period
    if days_since_last <= 7:
        scripture = '"Come to me, all you who are weary and burdened, and I will give you rest." — Matthew 11:28'
        message = "We noticed it's been a few days since your last conversation. How is your heart today?"
    elif days_since_last <= 30:
        scripture = '"The Lord is my shepherd, I lack nothing." — Psalm 23:1'
        message = "It's been a while since we last connected. We're here whenever you need spiritual guidance."
    else:
        scripture = '"For I know the plans I have for you," declares the Lord, "plans to prosper you and not to harm you, plans to give you hope and a future." — Jeremiah 29:11'
        message = "We miss you! Your spiritual journey is important to us. Come back anytime you need guidance."
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">How Is Your Heart Today? 💙</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Beloved Friend'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            {message}
        </p>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                {scripture}
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">Remember:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li>24/7 Biblical guidance is always available</li>
            <li>Your conversations are private and secure</li>
            <li>No struggle is too small to bring before God</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Continue Your Journey
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Walking with you in faith,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    # Add unsubscribe link for marketing emails
    if session_id:
        content = add_unsubscribe_footer(content, session_id, 'marketing')
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, 'We Miss You - Your Spiritual Journey Awaits', html)

def send_prayer_shared_notification(email, name, prayer_title, session_id=None):
    """Send notification when user's prayer receives engagement"""
    # Check preferences
    if session_id and not check_email_preferences(session_id, 'notifications'):
        logger.info(f"Skipping prayer notification for {email} - user opted out of notifications")
        return False
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Your Prayer is Helping Others! 🙏</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Faithful Servant'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            Your prayer "<strong>{prayer_title}</strong>" has been shared anonymously and is touching hearts in our community.
        </p>
        
        <div style="background: #dcfce7; border-left: 4px solid #16a34a; padding: 15px; margin: 20px 0;">
            <p style="color: #166534; margin: 0;">
                <strong>✨ Your faith is inspiring others!</strong><br>
                By sharing your prayer, you're helping fellow believers find strength and hope in God's word.
            </p>
        </div>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                "Let your light shine before others, that they may see your good deeds and glorify your Father in heaven."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 5px 0 0; text-align: right;">
                — Matthew 5:16
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org/app" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                View Community Prayers
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            May your faith continue to bless others,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    # Add unsubscribe link for notifications
    if session_id:
        content = add_unsubscribe_footer(content, session_id, 'notifications')
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, '🙏 Your Prayer is Inspiring Others!', html)

def get_unsubscribe_link(session_id, email_type='all'):
    """Generate unsubscribe link for emails"""
    return f"https://myconfessions.org/api/user/unsubscribe?session_id={session_id}&type={email_type}"

def add_unsubscribe_footer(content, session_id, email_type='all'):
    """Add unsubscribe link to email content"""
    unsubscribe_link = get_unsubscribe_link(session_id, email_type)
    return content + f'''
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
            <p style="color: #9ca3af; font-size: 11px; margin: 0;">
                Don't want to receive these emails? 
                <a href="{unsubscribe_link}" style="color: #6b7280; text-decoration: underline;">Unsubscribe</a>
            </p>
        </div>
    '''

def check_email_preferences(session_id, email_type):
    """Check if user wants to receive this type of email"""
    if not db or not session_id:
        return True  # Default to sending if we can't check
    
    try:
        user_ref = db.collection('users').document(session_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            preferences = user_data.get('email_preferences', {})
            return preferences.get(email_type, True)
        return True
    except Exception as e:
        logger.error(f"Error checking email preferences: {e}")
        return True  # Default to sending on error

def send_free_tier_upgrade_reminder(email, name, session_id=None):
    """Send gentle reminder about Premium benefits after user hits free tier limit"""
    # Check preferences
    if session_id and not check_email_preferences(session_id, 'marketing'):
        logger.info(f"Skipping free tier reminder for {email} - user opted out of marketing emails")
        return False
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Continue Your Spiritual Growth 🌱</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Seeker of Truth'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            We've noticed you've been actively seeking Biblical guidance. That's wonderful! Your dedication to spiritual growth is inspiring.
        </p>
        
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
            <p style="color: #92400e; margin: 0;">
                <strong>You've reached your free tier limit (20 conversations/month)</strong><br>
                Continue your journey with unlimited access
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">Premium Benefits:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li>💬 <strong>Unlimited conversations</strong> - No monthly limits</li>
            <li>📖 <strong>Community prayers</strong> - Read thousands of testimonies</li>
            <li>💾 <strong>Journey saved</strong> - Never lose your spiritual progress</li>
            <li>⚡ <strong>Priority support</strong> - Get help when you need it</li>
        </ul>
        
        <div style="background: #dcfce7; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <p style="color: #166534; margin: 0 0 10px; font-size: 18px;">
                <strong>Only $4.99/month</strong>
            </p>
            <p style="color: #166534; margin: 0; font-size: 14px;">
                Or save 33% with annual plan ($39.99/year)
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org/app" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Upgrade to Premium
            </a>
        </div>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <p style="color: #1e40af; font-style: italic; margin: 0;">
                "Ask and it will be given to you; seek and you will find; knock and the door will be opened to you."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 5px 0 0; text-align: right;">
                — Matthew 7:7
            </p>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Your partner in spiritual growth,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    # Add unsubscribe link for marketing emails
    if session_id:
        content = add_unsubscribe_footer(content, session_id, 'marketing')
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, '🌱 Continue Your Spiritual Journey with Premium', html)

def send_weekly_spiritual_insight(email, name, session_id=None):
    """Send weekly spiritual insight/encouragement email"""
    # Check preferences
    if session_id and not check_email_preferences(session_id, 'insights'):
        logger.info(f"Skipping weekly insight for {email} - user opted out of insights")
        return False
    
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Weekly Spiritual Insight 📖</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Child of God'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            This week, we invite you to reflect on God's grace in your daily life.
        </p>
        
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; margin: 25px 0;">
            <h3 style="color: #1e40af; margin: 0 0 15px;">This Week's Reflection:</h3>
            <p style="color: #1e40af; font-style: italic; margin: 0; font-size: 16px;">
                "Be still, and know that I am God; I will be exalted among the nations, I will be exalted in the earth."
            </p>
            <p style="color: #1e40af; font-size: 12px; margin: 10px 0 0; text-align: right;">
                — Psalm 46:10
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">Reflection Questions:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li>When do you find it hardest to "be still" in your daily life?</li>
            <li>How can you create more space for God's presence this week?</li>
            <li>What worries can you surrender to Him today?</li>
        </ul>
        
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
            <p style="color: #92400e; margin: 0;">
                <strong>💡 This Week's Practice:</strong><br>
                Take 5 minutes each morning to sit in silence with God. Let Him speak to your heart.
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Talk with Your Spiritual Guide
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Walking alongside you in faith,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    # Add unsubscribe link for insights
    if session_id:
        content = add_unsubscribe_footer(content, session_id, 'insights')
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, '📖 Weekly Spiritual Insight from My Confessions', html)

def send_subscription_renewal_reminder(email, name, renewal_date, amount):
    """Send reminder before subscription renewal"""
    content = f'''
        <h2 style="color: #1e40af; margin-top: 0;">Your Subscription Renews Soon</h2>
        
        <p style="color: #374151; line-height: 1.6;">
            Dear {name or 'Valued Member'},
        </p>
        
        <p style="color: #374151; line-height: 1.6;">
            This is a friendly reminder that your My Confessions Premium membership will automatically renew on <strong>{renewal_date}</strong>.
        </p>
        
        <div style="background: #eff6ff; border: 2px solid #3b82f6; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h3 style="color: #1e40af; margin: 0 0 10px;">Upcoming Renewal</h3>
            <p style="color: #1e40af; margin: 0; font-size: 24px; font-weight: bold;">
                ${amount}
            </p>
            <p style="color: #6b7280; margin: 10px 0 0; font-size: 14px;">
                {renewal_date}
            </p>
        </div>
        
        <h3 style="color: #1e40af; margin-top: 25px;">You'll Continue Enjoying:</h3>
        <ul style="color: #374151; line-height: 1.8;">
            <li>Unlimited Biblical guidance 24/7</li>
            <li>Access to all community prayers</li>
            <li>Your complete spiritual journey saved</li>
            <li>Priority support from our ministry</li>
        </ul>
        
        <p style="color: #374151; line-height: 1.6; margin-top: 25px;">
            No action needed - your subscription will renew automatically. If you need to make changes, 
            you can manage your subscription anytime.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://myconfessions.org/app" 
               style="background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                Manage Subscription
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            Thank you for your continued partnership,<br>
            <strong>My Confessions Ministry</strong>
        </p>
    '''
    
    html = EMAIL_BASE_TEMPLATE.format(content=content)
    return send_email(email, f'Subscription Renewal Reminder - {renewal_date}', html)

# Initialize Firebase Admin SDK
try:
    # Try multiple possible locations for credentials file
    import os
    possible_paths = [
        "firebase-credentials.json",
        "/app/firebase-credentials.json",
        os.path.join(os.path.dirname(__file__), "firebase-credentials.json")
    ]
    
    cred_file = None
    for path in possible_paths:
        if os.path.exists(path):
            cred_file = path
            logger.info(f"Found Firebase credentials at: {path}")
            break
    
    if cred_file:
        cred = credentials.Certificate(cred_file)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase Firestore initialized successfully.")
    else:
        logger.error("Firebase credentials file not found in any expected location")
        logger.warning(f"Checked paths: {possible_paths}")
        db = None
except Exception as e:
    logger.error(f"Could not initialize Firebase Admin SDK: {e}")
    logger.warning("Falling back to in-memory storage. THIS IS NOT SUITABLE FOR PRODUCTION.")
    db = None

# In-memory storage is now a fallback for local development without credentials.
confessions = [] # This will only be used if Firestore fails to initialize.
conversations = {}

# Value-first user tracking system
user_sessions = {}  # Track user subscription status (in-memory cache)
conversation_depth = {}  # Track conversation engagement
password_reset_tokens = {}  # Track password reset tokens {token: {email, expires}}
from datetime import datetime, timedelta
import calendar
import json
import secrets
import time

def get_user_tier(session_id):
    """Get user subscription tier: 'free' or 'unlimited'"""
    return user_sessions.get(session_id, {}).get('tier', 'free')

def get_conversation_depth(session_id):
    """Get current conversation depth (number of messages)"""
    return conversation_depth.get(session_id, 0)

def increment_conversation_depth(session_id):
    """Increment conversation depth counter"""
    conversation_depth[session_id] = conversation_depth.get(session_id, 0) + 1

def should_suggest_upgrade(session_id):
    """Suggest upgrade after 20 meaningful messages (value demonstration)"""
    depth = get_conversation_depth(session_id)
    tier = get_user_tier(session_id)
    
    # Suggest upgrade after 20 messages for free users
    return tier == 'free' and depth >= 20

def set_user_tier(session_id, tier, customer_id=None, subscription_id=None):
    """Set user subscription tier (for testing and webhook handling)"""
    if session_id not in user_sessions:
        user_sessions[session_id] = {}
    user_sessions[session_id]['tier'] = tier
    user_sessions[session_id]['updated_at'] = datetime.now()
    if customer_id:
        user_sessions[session_id]['customer_id'] = customer_id
    if subscription_id:
        user_sessions[session_id]['subscription_id'] = subscription_id
    
    # Also store in Firestore for persistence
    try:
        if db:
            subscription_data = {
                'tier': tier,
                'session_id': session_id,
                'updated_at': datetime.now(),
                'created_at': user_sessions[session_id].get('created_at', datetime.now())
            }
            if customer_id:
                subscription_data['customer_id'] = customer_id
            if subscription_id:
                subscription_data['subscription_id'] = subscription_id
                
            subscription_ref = db.collection('subscriptions').document(session_id)
            subscription_ref.set(subscription_data)
            logger.info(f"Stored subscription {tier} for session {session_id} in Firestore")
    except Exception as e:
        logger.error(f"Failed to store subscription in Firestore: {e}")

def load_user_subscriptions():
    """Load user subscriptions from Firestore on startup"""
    try:
        if db:
            subscriptions = db.collection('subscriptions').stream()
            for sub in subscriptions:
                data = sub.to_dict()
                session_id = data.get('session_id', sub.id)
                user_sessions[session_id] = {
                    'tier': data.get('tier', 'free'),
                    'updated_at': data.get('updated_at', datetime.now()),
                    'created_at': data.get('created_at', datetime.now())
                }
            logger.info(f"Loaded {len(user_sessions)} subscriptions from Firestore")
    except Exception as e:
        logger.error(f"Failed to load subscriptions from Firestore: {e}")

def get_subscription_from_stripe_session(stripe_session_id):
    """Get subscription details from Stripe session"""
    try:
        session = stripe.checkout.Session.retrieve(stripe_session_id)
        if session.payment_status == 'paid':
            return {
                'customer_id': session.customer,
                'subscription_id': session.subscription,
                'session_id': session.metadata.get('user_session_id', 'anonymous'),
                'tier': session.metadata.get('tier', 'unlimited')
            }
    except Exception as e:
        logger.error(f"Failed to get Stripe session: {e}")
    return None

# Initialize OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key and openai_api_key.startswith('sk-'):
    logger.info("OpenAI API key found")
else:
    logger.warning("No valid OpenAI API key found")
    openai_api_key = None

# Initialize Stripe
stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')

if stripe_secret_key:
    try:
        stripe.api_key = stripe_secret_key
        logger.info("Stripe API key found and configured")
    except Exception as e:
        logger.error(f"Stripe initialization error: {e}")
else:
    logger.warning("No Stripe API key found")

# Christian Spiritual Counselor Prompts
CONFESSION_INITIAL_PROMPT = """You are a wise and compassionate Biblical counselor and spiritual guide.

FIRST MESSAGE ONLY – Responsibilities:
1. Offer a warm, safe, and non-judgmental welcome (1 sentence).
2. Provide 1–2 short Scripture references that offer hope and peace (1–2 sentences).
3. Ask one gentle, open-ended question to help the user share what is on their heart (1 sentence).

Keep the whole reply under 4 sentences. Your tone should be warm, supportive, and encouraging, like a wise friend.
"""

CONFESSION_FOLLOWUP_PROMPT = """You are a wise and compassionate Biblical counselor and spiritual guide. Your goal is to create a natural, reflective, and supportive conversation.

**Your Role in This Follow-Up Message:**
1.  **Acknowledge & Validate**: Start by acknowledging the user's last message with deep empathy (e.g., "I hear the pain in your words," "It is understandable that you feel this way," "Thank you for trusting me with this.").
2.  **Offer Gentle Guidance**: Provide a *brief* spiritual insight or a *new, relevant* Scripture verse that directly addresses their specific concern (1-2 sentences). Focus on God's love, grace, and peace.
3.  **Decide How to Conclude**:
    -   **Option A (Ask a Question):** If the conversation needs prompting, ask a single, gentle, open-ended question to help them reflect or share more.
    -   **Option B (Make a Statement):** If the user has shared something positive or conclusive, simply offer an affirming statement of blessing or peace.

**Crucial Constraints:**
-   **VARY YOUR RESPONSES**: Do NOT ask a question every single time.
-   **Be Concise**: Never exceed 4 sentences.
-   **Be Supportive**: Your tone should be gentle, patient, and kind. Avoid being overly dogmatic or preachy.
-   **No Repetition**: Do not repeat the initial welcome or previous scripture.
"""

CONFESSION_SUMMARY_PROMPT = """Transform this conversation for anonymous sharing while keeping it authentic.

Guidelines:
1. Remove specific names, places, and overly personal details
2. Keep it brief and natural (2-4 sentences - follow the natural flow)
3. Preserve the authentic voice and emotional truth
4. Include Scripture reference if it was mentioned in the conversation
5. Don't force a structure - let it flow naturally

Title: Create a simple, relatable title (3-5 words)
Examples: "Struggling with Anxiety", "Finding Peace", "A Mother's Prayer"

Prayer: Keep the person's authentic voice. Natural, not templated.

Example:
Input: "I've been so angry at my wife over money. We argue constantly."
Output:
Title: Anger in Marriage
Prayer: I've struggled with anger toward my spouse over financial stress. Through prayer and Ephesians 4:26, I'm learning that holding onto anger only hurts us both. I'm asking God for patience to forgive daily.

Keep it REAL, NATURAL, and AUTHENTIC - not a formulaic prayer template.

Output Format (MUST follow):
Title: [simple title]
Prayer: [natural, authentic confession]
"""

@app.route('/')
def index_redirect():
    """Serve the landing page"""
    return render_template('index.html')

@app.route('/app')
def app_view():
    """Main confession app"""
    # Firebase configuration for frontend
    firebase_config = {
        'apiKey': os.getenv('FIREBASE_API_KEY', ''),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
        'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', ''),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
        'appId': os.getenv('FIREBASE_APP_ID', '')
    }
    
    return render_template('app.html', 
                         cache_bust=datetime.now().timestamp(),
                         firebase_config=firebase_config)

@app.route('/terms')
def terms_view():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy_view():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/disclaimer')
def disclaimer_view():
    """Disclaimer page"""
    return render_template('disclaimer.html')

@app.route('/subscription-success')
def subscription_success():
    """Handle successful subscription"""
    stripe_session_id = request.args.get('session_id')
    user_session = request.args.get('user_session', 'anonymous')
    
    # Get subscription details from Stripe
    subscription_data = get_subscription_from_stripe_session(stripe_session_id)
    
    if subscription_data:
        # Upgrade user based on actual Stripe data
        session_id = subscription_data['session_id']
        tier = subscription_data['tier']
        customer_id = subscription_data.get('customer_id')
        subscription_id = subscription_data.get('subscription_id')
        
        set_user_tier(session_id, tier, customer_id, subscription_id)
        
        # Also update the user's account in the users collection if it exists
        if db:
            try:
                user_ref = db.collection('users').document(session_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    # Update existing user account with subscription info
                    user_ref.update({
                        'tier': tier,
                        'customer_id': customer_id,
                        'subscription_id': subscription_id,
                        'updated_at': datetime.now()
                    })
                    logger.info(f"Updated user account {session_id} with subscription info")
                else:
                    # Check if this session_id corresponds to a registered user by email
                    # This handles cases where user registered but session_id doesn't match
                    users_ref = db.collection('users')
                    users_query = users_ref.where('session_id', '==', session_id).limit(1).get()
                    
                    if users_query:
                        user_ref = users_ref.document(users_query[0].id)
                        user_ref.update({
                            'tier': tier,
                            'customer_id': customer_id,
                            'subscription_id': subscription_id,
                            'updated_at': datetime.now()
                        })
                        logger.info(f"Updated user account {users_query[0].id} with subscription info")
            except Exception as e:
                logger.error(f"Failed to update user account: {e}")
        
        logger.info(f"User {session_id} upgraded to {tier} via Stripe session {stripe_session_id}")
        
        return render_template('subscription-success.html', 
                             tier=tier, 
                             session_id=session_id,
                             subscription_id=subscription_id,
                             customer_id=customer_id)
    else:
        # Fallback: upgrade the user session from URL parameter
        set_user_tier(user_session, 'unlimited')
        
        # Also update user account if it exists
        if db:
            try:
                user_ref = db.collection('users').document(user_session)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_ref.update({
                        'tier': 'unlimited',
                        'updated_at': datetime.now()
                    })
                    logger.info(f"Updated user account {user_session} with unlimited tier (fallback)")
            except Exception as e:
                logger.error(f"Failed to update user account (fallback): {e}")
        
        logger.info(f"User {user_session} upgraded to unlimited (fallback)")
        
        return render_template('subscription-success.html', tier='unlimited', session_id=user_session)

@app.route('/subscription-cancel')
def subscription_cancel():
    """Handle cancelled subscription"""
    return render_template('subscription-cancel.html')

@app.route('/api/user/tier', methods=['GET'])
def get_user_tier_api():
    """Get current user tier and usage"""
    session_id = request.args.get('session_id', 'anonymous')
    return jsonify({
        'tier': get_user_tier(session_id),
        'conversation_depth': get_conversation_depth(session_id),
        'limit': 999 if get_user_tier(session_id) == 'unlimited' else 20
    })

@app.route('/api/user/tier', methods=['POST'])
def set_user_tier_api():
    """Set user tier (for testing purposes)"""
    data = request.get_json()
    session_id = data.get('session_id', 'anonymous')
    tier = data.get('tier', 'free')
    
    if tier not in ['free', 'unlimited']:
        return jsonify({'error': 'Invalid tier'}), 400
    
    set_user_tier(session_id, tier)
    return jsonify({'success': True, 'tier': tier})

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return app.send_static_file('manifest.json')

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt"""
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml"""
    return app.send_static_file('sitemap.xml')

@app.route('/api/stripe/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session for unlimited spiritual guidance"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'anonymous')
        plan = data.get('plan', 'monthly')  # 'monthly' or 'annual'
        
        if not stripe_secret_key:
            return jsonify({'error': 'Payment processing is not available'}), 503
            
        # Get price ID based on selected plan
        if plan == 'annual':
            price_id = os.getenv('STRIPE_PRICE_ID_ANNUAL')
        else:
            price_id = os.getenv('STRIPE_PRICE_ID_UNLIMITED')
            
        if not price_id:
            # For testing purposes, use a placeholder
            # In production, you need to create the actual Stripe product
            return jsonify({
                'error': 'Stripe product not set up yet. Please create "Unlimited Spiritual Guidance" product in Stripe Dashboard and add STRIPE_PRICE_ID_UNLIMITED to your .env file.',
                'setup_required': True,
                'stripe_dashboard': 'https://dashboard.stripe.com/products'
            }), 500
            
        # Create checkout session
        try:
            logger.info(f"Creating Stripe unlimited subscription checkout")
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.host_url + f'subscription-success?session_id={{CHECKOUT_SESSION_ID}}&user_session={session_id}',
                cancel_url=request.host_url + 'app?cancelled=true',
                metadata={
                    'tier': 'unlimited',
                    'user_session_id': session_id,
                    'plan': plan,  # 'monthly' or 'annual'
                    'source': 'myconfessions_unlimited'
                },
                allow_promotion_codes=True,
            )
            logger.info(f"Stripe checkout session created: {checkout_session.id}")
        except Exception as stripe_error:
            logger.error(f"Stripe checkout error: {stripe_error}")
            return jsonify({'error': 'Unable to create payment session'}), 500
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Unable to process subscription'}), 500

@app.route('/api/stripe/config')
def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    return jsonify({
        'publishable_key': stripe_publishable_key
    })

@app.route('/api/chat/message', methods=['POST'])
def process_chat_message():
    """Handle chat messages for confession guidance"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', 'anonymous')
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        logger.info(f"Processing confession chat for session {session_id}")
        
        # Generate AI response - ONLY use real AI, no fallbacks
        if not openai_api_key:
            return jsonify({'error': 'AI service is not available. Please try again later.'}), 503
        
        try:
            # Decide which system prompt to use based on whether we already have conversation history
            if conversation_history:
                system_prompt = CONFESSION_FOLLOWUP_PROMPT
            else:
                system_prompt = CONFESSION_INITIAL_PROMPT

            # Build conversation context
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (unlimited for all users - we want to show value)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                
            for msg in recent_history:
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
            
            # Add current message
            messages.append({"role": "user", "content": message})
                
            # Make direct API call
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 120,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return jsonify({'error': 'Sorry, I cannot connect to the AI system right now. Please try again later.'}), 500
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return jsonify({'error': 'Sorry, I cannot connect to the AI system right now. Please try again later.'}), 500
        
        # Store conversation in memory
        if session_id not in conversations:
            conversations[session_id] = []
        
        conversations[session_id].extend([
            {'role': 'user', 'content': message, 'timestamp': datetime.now().isoformat()},
            {'role': 'assistant', 'content': ai_response, 'timestamp': datetime.now().isoformat()}
        ])
        
        # INCREMENT CONVERSATION DEPTH
        increment_conversation_depth(session_id)
        
        # CHECK IF WE SHOULD SUGGEST UPGRADE (value-first approach)
        suggest_upgrade = should_suggest_upgrade(session_id)
        
        # Send upgrade reminder email when user hits limit (only once)
        current_depth = get_conversation_depth(session_id)
        if current_depth == 20 and get_user_tier(session_id) == 'free':
            # Get user email if they're registered
            if db:
                try:
                    user_ref = db.collection('users').document(session_id)
                    user_doc = user_ref.get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        user_email = user_data.get('email')
                        user_name = user_data.get('name', '')
                        
                        if user_email:
                            send_free_tier_upgrade_reminder(user_email, user_name, session_id)
                            logger.info(f"Free tier upgrade reminder sent to {user_email}")
                except Exception as e:
                    logger.error(f"Failed to send upgrade reminder: {e}")
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'tier': get_user_tier(session_id),
            'conversation_depth': get_conversation_depth(session_id),
            'suggest_upgrade': suggest_upgrade,  # NEW: Suggest upgrade instead of blocking
            'upgrade_message': {
                'title': 'Continue Your Spiritual Journey',
                'message': 'I sense you\'re seeking deeper guidance. Many souls like you find unlimited spiritual support helps them grow closer to God.',
                'cta': 'Continue with Unlimited Guidance - $4.99/month'
            } if suggest_upgrade else None
        })
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({'error': 'Sorry, something went wrong. Please try again.'}), 500

# ... rest of the file ...