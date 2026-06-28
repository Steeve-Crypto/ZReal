import os
import sys
from pathlib import Path

import environ

env = environ.Env(
    REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA=(bool, False),
    PROPERTY_DATA_ENABLE_LIVE_CALLS=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-zreal-dev-key-change-in-prod-!!!')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
FRONTEND_ORIGIN = env('FRONTEND_ORIGIN', default='http://127.0.0.1:3000')
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[FRONTEND_ORIGIN, 'http://localhost:3000'])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=CORS_ALLOWED_ORIGINS)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'channels',
    'rest_framework',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'properties',
    'core',
    'zcash_integration',
    'ai_valuation',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'zreal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.frontend_origin',
            ],
        },
    },
]

WSGI_APPLICATION = 'zreal.wsgi.application'
ASGI_APPLICATION = 'zreal.asgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ZCASH_RPC_URL = env('ZCASH_RPC_URL', default='')
if not ZCASH_RPC_URL:
    ZCASHRPC_USER = env('ZCASHRPC_USER', default='')
    ZCASHRPC_PASSWORD = env('ZCASHRPC_PASSWORD', default='')
    ZCASHRPC_HOST = env('ZCASHRPC_HOST', default='')
    ZCASHRPC_PORT = env('ZCASHRPC_PORT', default='18232')
    if ZCASHRPC_USER and ZCASHRPC_PASSWORD and ZCASHRPC_HOST:
        ZCASH_RPC_URL = f"http://{ZCASHRPC_USER}:{ZCASHRPC_PASSWORD}@{ZCASHRPC_HOST}:{ZCASHRPC_PORT}"
else:
    ZCASHRPC_USER = env('ZCASHRPC_USER', default='')
    ZCASHRPC_PASSWORD = env('ZCASHRPC_PASSWORD', default='')
    ZCASHRPC_HOST = env('ZCASHRPC_HOST', default='')
    ZCASHRPC_PORT = env('ZCASHRPC_PORT', default='18232')

ZCASH_NETWORK = env('ZCASH_NETWORK', default='testnet')
ZSA_ISSUANCE_BACKEND = env('ZSA_ISSUANCE_BACKEND', default='zcash_tx_tool')
ZCASH_TX_TOOL_PATH = env('ZCASH_TX_TOOL_PATH', default='')
ZCASH_ZSA_ISSUE_COMMAND = env(
    'ZCASH_ZSA_ISSUE_COMMAND',
    default='{tool} create-zsa-issuance --from {issuer_zaddr} --asset-symbol {asset_symbol} --total-shares {total_shares} --network {network}'
)
ZCASH_ZSA_STATUS_COMMAND = env(
    'ZCASH_ZSA_STATUS_COMMAND',
    default='{tool} status --operation-id {operation_id} --network {network}'
)

STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_ISSUER_PRICE_ID = env('STRIPE_ISSUER_PRICE_ID', default='')
REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA = env('REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA')

PROPERTY_DATA_PROVIDER = env('PROPERTY_DATA_PROVIDER', default='mock')
PROPERTY_DATA_ENABLE_LIVE_CALLS = env('PROPERTY_DATA_ENABLE_LIVE_CALLS')
PROPERTY_DATA_API_KEY = env('PROPERTY_DATA_API_KEY', default='')
PROPERTY_DATA_REGRID_API_KEY = env('PROPERTY_DATA_REGRID_API_KEY', default=env('REGRID_API_KEY', default=''))
PROPERTY_DATA_OPENCAGE_API_KEY = env('PROPERTY_DATA_OPENCAGE_API_KEY', default=env('OPENCAGE_API_KEY', default=''))
PROPERTY_DATA_GOOGLE_API_KEY = env('PROPERTY_DATA_GOOGLE_API_KEY', default=env('GOOGLE_GEOCODING_API_KEY', default=''))

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ]
}

# ==================== ALLAUTH CONFIG ====================
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Change to 'mandatory' in production

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ==================== DJ-STRIPE CONFIG ====================
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = env('DJSTRIPE_WEBHOOK_SECRET', default='')
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
