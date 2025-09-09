# models.py
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
from datetime import datetime

# URL短縮リクエストモデル
class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None
    
    @validator('url')
    def validate_url(cls, v):
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URLはhttp://またはhttps://で始まる必要があります')
        return v

# URL短縮レスポンスモデル
class ShortenResponse(BaseModel):
    success: bool
    short_url: str
    short_code: str
    original_url: str
    qr_code_url: str
    created_at: str
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

# 一括生成リクエストモデル
class BulkRequest(BaseModel):
    urls: List[dict]
    campaign_name: Optional[str] = None

# 一括生成レスポンスモデル
class BulkResponse(BaseModel):
    success: bool
    processed_count: int
    results: List[ShortenResponse]
    errors: List[str] = []

# 分析データモデル
class AnalyticsData(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    unique_clicks: int
    qr_clicks: int
    created_at: str
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None
    click_history: List[dict] = []

# クリック詳細モデル
class ClickDetail(BaseModel):
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    source: str = "direct"
    clicked_at: str

# システム統計モデル
class SystemStats(BaseModel):
    total_urls: int
    total_clicks: int
    unique_visitors: int
    top_urls: List[dict] = []

# エラーレスポンスモデル
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None

