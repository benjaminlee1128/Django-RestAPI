import sys

from settings import *

DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': os.getenv('SILVER_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('SILVER_DB_NAME', 'db.sqlite3'),
        'USER': os.getenv('SILVER_DB_USER', 'silver'),
        'PASSWORD': os.getenv('SILVER_DB_PASSWORD', 'password'),
        'HOST': os.getenv('SILVER_DB_HOST', ''),
        'PORT': os.getenv('SILVER_DB_PORT', '3306'),
        'TEST': {
            'CHARSET': 'utf8'
        }
    }
}

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']

if 'test' in sys.argv:
    # faster tests
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
        'django.contrib.auth.hashers.BCryptPasswordHasher',
        'django.contrib.auth.hashers.SHA1PasswordHasher',
        'django.contrib.auth.hashers.CryptPasswordHasher',
    ]
    DEBUG = False
    TEMPLATE_DEBUG = False

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite',
        }
    }
