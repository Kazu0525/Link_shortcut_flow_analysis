# routes/__init__.py
from .redirect import router as redirect_router
from .shorten import router as shorten_router
from .analytics import router as analytics_router
from .bulk import router as bulk_router
from .export import router as export_router
from .admin import router as admin_router

# バージョン情報を追加（エラー解消のため）
__version__ = "1.0.0"
__author__ = "koji"
__description__ = "URL Shortener API Routes"

__all__ = [
    'redirect_router',
    'shorten_router', 
    'analytics_router',
    'bulk_router',
    'export_router',
    'admin_router'
]
