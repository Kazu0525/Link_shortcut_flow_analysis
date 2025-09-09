# models.py - Rust依存なし（pydantic除去）
from datetime import datetime
from typing import Optional, List, Dict, Any

# シンプルなクラス定義（pydantic不使用）
class ShortenRequest:
    def __init__(self, original_url: str, custom_name: Optional[str] = None, campaign_name: Optional[str] = None):
        self.original_url = original_url
        self.custom_name = custom_name
        self.campaign_name = campaign_name

class ShortenResponse:
    def __init__(self, short_code: str, short_url: str, original_url: str, qr_code_url: str, 
                 created_at: str, custom_name: Optional[str] = None, campaign_name: Optional[str] = None):
        self.short_code = short_code
        self.short_url = short_url
        self.original_url = original_url
        self.qr_code_url = qr_code_url
        self.created_at = created_at
        self.custom_name = custom_name
        self.campaign_name = campaign_name
    
    def dict(self):
        return {
            "short_code": self.short_code,
            "short_url": self.short_url,
            "original_url": self.original_url,
            "qr_code_url": self.qr_code_url,
            "created_at": self.created_at,
            "custom_name": self.custom_name,
            "campaign_name": self.campaign_name
        }

class ClickData:
    def __init__(self, id: int, ip_address: str, user_agent: str, referrer: str, source: str, clicked_at: datetime):
        self.id = id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.referrer = referrer
        self.source = source
        self.clicked_at = clicked_at

class AnalyticsResponse:
    def __init__(self, short_code: str, total_clicks: int, unique_visitors: int, qr_clicks: int, click_data: List[ClickData]):
        self.short_code = short_code
        self.total_clicks = total_clicks
        self.unique_visitors = unique_visitors
        self.qr_clicks = qr_clicks
        self.click_data = click_data

# 軽量版バルクリクエスト
class BulkItem:
    def __init__(self, url: str, custom_name: Optional[str] = None):
        self.url = url
        self.custom_name = custom_name

class BulkRequest:
    def __init__(self, urls: List[Dict], campaign_name: Optional[str] = None):
        self.urls = [BulkItem(url=item.get("url"), custom_name=item.get("custom_name")) for item in urls]
        self.campaign_name = campaign_name

class BulkResponseItem:
    def __init__(self, original_url: str, short_code: str, short_url: str, qr_code_url: str = "",
                 custom_name: Optional[str] = None, success: bool = True, error_message: Optional[str] = None):
        self.original_url = original_url
        self.short_code = short_code
        self.short_url = short_url
        self.qr_code_url = qr_code_url
        self.custom_name = custom_name
        self.success = success
        self.error_message = error_message

class BulkResponse:
    def __init__(self, results: List[BulkResponseItem], total_count: int, success_count: int, 
                 failed_count: int, campaign_name: Optional[str] = None):
        self.results = results
        self.total_count = total_count
        self.success_count = success_count
        self.failed_count = failed_count
        self.campaign_name = campaign_name

# エクスポート用
class ExportRequest:
    def __init__(self, short_codes: List[str], format: str = "json"):
        self.short_codes = short_codes
        self.format = format

# その他のデータクラス
class AnalyticsData:
    def __init__(self, short_code: str, total_clicks: int, unique_visitors: int, qr_clicks: int,
                 last_clicked: Optional[datetime] = None):
        self.short_code = short_code
        self.total_clicks = total_clicks
        self.unique_visitors = unique_visitors
        self.qr_clicks = qr_clicks
        self.last_clicked = last_clicked

class SystemStats:
    def __init__(self, total_links: int, total_clicks: int, total_qr_clicks: int, system_status: str):
        self.total_links = total_links
        self.total_clicks = total_clicks
        self.total_qr_clicks = total_qr_clicks
        self.system_status = system_status

class ErrorResponse:
    def __init__(self, error: str, detail: Optional[str] = None):
        self.error = error
        self.detail = detail
