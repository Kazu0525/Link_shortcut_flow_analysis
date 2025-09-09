# models.py
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
from datetime import datetime

# 既存のモデルに加えて以下を追加

# 元のShortenRequestとの互換性を保つため
class ShortenRequest(BaseModel):
    original_url: HttpUrl  # url → original_url に変更
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None
    
    @validator('original_url')
    def validate_url(cls, v):
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URLはhttp://またはhttps://で始まる必要があります')
        return v

# インポートで要求されているShortenResponse
class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    qr_code_url: str
    created_at: str
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

# クリックデータモデル（analyticsで必要）
class ClickData(BaseModel):
    id: int
    ip_address: str
    user_agent: str
    referrer: str
    source: str
    clicked_at: datetime

# 分析レスポンスモデル
class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    unique_visitors: int
    qr_clicks: int
    click_data: List[ClickData]

# エクスポートリクエストモデル
class ExportRequest(BaseModel):
    short_codes: List[str]
    format: str = "json"

# バルクリクエストアイテム
class BulkItem(BaseModel):
    url: HttpUrl
    custom_name: Optional[str] = None

# 一括生成リクエスト（修正版）
class BulkRequest(BaseModel):
    urls: List[BulkItem]
    campaign_name: Optional[str] = None

# models.py の最後に追加
class BulkResponseItem(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    qr_code_url: str
    custom_name: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class BulkResponse(BaseModel):
    results: List[BulkResponseItem]
    total_count: int
    success_count: int
    failed_count: int
    campaign_name: Optional[str] = None

# models.py に以下のクラスを追加
class AnalyticsData(BaseModel):
    short_code: str
    total_clicks: int
    unique_visitors: int
    qr_clicks: int
    last_clicked: Optional[datetime] = None
    created_at: datetime

class ClickDetail(BaseModel):
    id: int
    ip_address: str
    user_agent: str
    referrer: str
    source: str
    clicked_at: datetime

class SystemStats(BaseModel):
    total_links: int
    total_clicks: int
    total_qr_clicks: int
    system_status: str

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

