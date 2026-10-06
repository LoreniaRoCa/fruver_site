"""
Django settings for sistema_evaluacion project.
"""
from pathlib import Path
from django.urls import reverse_lazy

import os
import unfold
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar el archivo .env ubicado junto a manage.py
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*']

# Forzar seguridad de CSRF y Cookies en producción detrás de Apache Proxy
CSRF_TRUSTED_ORIGINS = [
    'https://rh.fruver.com.mx',
    'http://rh.fruver.com.mx',
]

# Indicar a Django que considere segura la conexión del proxy de DreamHost
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Si el proxy no envía X-Forwarded-Proto, forzamos CSRF a usar HTTPS
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ==========================================
# CONFIGURACIÓN SMTP DIRECTA PARA DREAMHOST
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')        # O mail.fruver.com.mx
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 10

INSTALLED_APPS = [
    'unfold',  # Primero la estructura base de Unfold
    'unfold.contrib.filters',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rh.apps.RhConfig',
    'reportes.apps.ReportesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', # Garantiza la traducción del Admin
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 🟢 Tu nuevo middleware de restricción de menú:
    'rh.middleware.RestringirAccesoAdminMiddleware',
]

ROOT_URLCONF = 'core.urls'

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'rh' / 'templates'], 
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#                 'django.template.context_processors.i18n',
#             ],
#         },
#     },
# ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
                    BASE_DIR / 'templates',
                    BASE_DIR / 'rh' / 'templates',
                    BASE_DIR / 'reportes' / 'templates',  # <-- AGREGAR ESTA LÍNEA
                    BASE_DIR / 'reportes' / 'templates',  # 🌟 Permite cargar plantillas como 'reportes/inventario_pivot.html'
                ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'rh.context_processors.empresa_activa',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

db_port = os.environ.get('DB_PORT')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': int(db_port) if db_port and db_port.isdigit() else 6543,
        'OPTIONS': {
            'options': '-c search_path=public'
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================================================================
# CONFIGURACIÓN DE IDIOMA Y REGIÓN (CORREGIDO PARA ACTIVAR TRADUCCIONES)
# =========================================================================

LANGUAGE_CODE = 'es' # Usamos 'es' estándar para que Unfold active sus traducciones Gettext
TIME_ZONE = 'America/Mexico_City'

USE_I18N = True
USE_TZ = True
USE_L10N = True # Activado para que traduzca componentes de interfaz de paquetes externos

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# 🔴 Comentamos esta línea para eliminar el WARNING W004:
# STATICFILES_DIRS = [ BASE_DIR / 'static' ]

# 🟢 Le indicamos a Django la ubicación FÍSICA de Unfold sin duplicar:
STATICFILES_DIRS = [
    os.path.join(os.path.dirname(unfold.__file__), 'static'),
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


# Redirecciones tras autenticación
#LOGIN_REDIRECT_URL = '/admin/'  # O la ruta principal de tu sistema
LOGIN_REDIRECT_URL = 'redireccionar_login'
LOGOUT_REDIRECT_URL = '/admin/login/'

# Configuración de Proxies (Requerido para DreamHost, Render, Heroku, etc.)
# En local no afecta en absoluto.
# =========================================================================
# CONFIGURACIÓN DE DJANGO UNFOLD (DASHBOARD ACTIVADO Y PISTACHE THEME)
# =========================================================================
# =========================================================================
# CONFIGURACIÓN DE DJANGO UNFOLD (DASHBOARD ACTIVADO + TRADUCCIÓN COMPLETA)
# =========================================================================
UNFOLD = {
    "SITE_TITLE": "Recursos Humanos",
    "SITE_HEADER": "Recursos Humanos",
    "SIDEBAR_CHANGED": False, 
    "SEARCH_PLACEHOLDER": "Buscar...",
    "DASHBOARD_CALLBACK": None, 
    
    "COLORS": {
        "primary": {
            "50": "#f4f9f1",   
            "100": "#e6f3df",
            "200": "#cfe7c2",
            "300": "#b1d79c",  
            "400": "#93c375",
            "500": "#72a651",  # Verde Pistache Central
            "600": "#5b893f",  
            "700": "#476b32",  
            "800": "#3a562b",
            "900": "#314925",
            "950": "#1a2912",
        },
    },
    
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False, # 🌟 Oculta aplicaciones por defecto
        "navigation": [
            {
                "title": "Evaluaciones de Desempeño",
                "separator": True,
                "items": [
                    {
                        "title": "Mi Panel de Evaluación",
                        "link": "/admin/panel-evaluacion/", 
                        "icon": "badge",
                        # 🟢 Visible para TODOS los usuarios que inicien sesión
                        #"permission": lambda request: request.user.is_authenticated,
                    },
                    {
                        "title": "Consolidado Resultados",
                        "link": "/admin/resumen-evaluaciones/", 
                        "icon": "analytics",
                        # 🔴 Solo para Administradores
                        #"permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Asignación de Competencias",
                        "link": reverse_lazy("asignacion_competencias"),
                        "icon": "assignment",
                        # 🔴 Solo para Administradores
                        #"permission": lambda request: request.user.is_superuser,
                    },
                ]
            },
            # 🟢 NUEVO BLOQUE DE REPORTES Y TABLAS DINÁMICAS
            {
                "title": "Reportes y Análisis",
                "separator": True,
                "items": [
                    {
                        "title": "Inventario Pivot",
                        "link": "/inventario/pivot/",  # Ruta configurada en urls.py
                        "icon": "bar_chart",           # Icono de Material Icons
                    },
                ],
            },
            {
                "title": "Catálogos del Sistema",
                "separator": True,
                # 🔴 Solo para Administradores (Oculto para empleados normales)
                #"permission": lambda request: request.user.is_superuser,
                "items": [
                    {
                        "title": "Empleados",
                        "link": "/admin/rh/empleado/",
                        "icon": "people",
                    },
                    {
                        "title": "Puestos",
                        "link": "/admin/rh/puesto/",
                        "icon": "work",
                    },
                    {
                        "title": "Departamentos",
                        "link": "/admin/rh/departamento/",
                        "icon": "domain",
                    },
                    {
                        "title": "Competencias",
                        "link": "/admin/rh/competencia/",
                        "icon": "star",
                    },
                    {
                        "title": "Clasificación de Competencias",
                        "link": "/admin/rh/competenciaclasificacion/",
                        "icon": "layers",
                    },
                    {
                        "title": "Configurar Evaluaciones",
                        "icon": "event_note",
                        "link": "/admin/rh/evaluacion/", 
                    },                    
                ],
            },
            {
                "title": "Seguridad del Sitio",
                "separator": True,
                # 🔴 Solo para Administradores
                #"permission": lambda request: request.user.is_superuser,
                "items": [
                    {
                        "title": "Usuarios",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "icon": "people",
                    },
                    {
                        "title": "Grupos y Permisos",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "icon": "gavel",
                    },
                ],
            },
        ],
    },
}
