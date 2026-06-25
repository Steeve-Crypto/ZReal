import os
from pathlib import Path

import environ

env = environ.Env(
    REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-zreal-dev-key-change-in-prod-!!!')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

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
    zcash_user = env('ZCASHRPC_USER', default='')
    zcash_password = env('ZCASHRPC_PASSWORD', default='')
    zcash_host = env('ZCASHRPC_HOST', default='')
    zcash_port = env('ZCASHRPC_PORT', default='18232')
    if zcash_user and zcash_password and zcash_host:
        ZCASH_RPC_URL = f"http://{zcash_user}:{zcash_password}@{zcash_host}:{zcash_port}"

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
