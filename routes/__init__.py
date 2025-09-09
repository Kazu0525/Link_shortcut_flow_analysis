# routes/__init__.py
# 全ての相対インポートを絶対インポートに変更 + qrcode関連を完全除去

from routes.redirect import router as redirect_router
from routes.shorten import router as shorten_router  
from routes.analytics import router as analytics_router
from routes.bulk import router as bulk_router
from routes.export import router as export_router
from routes.admin import router as admin_router

__all__ = [
    "redirect_router",
    "shorten_router", 
    "analytics_router",
    "bulk_router",
    "export_router",
    "admin_router"
]
