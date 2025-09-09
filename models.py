from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
from datetime import datetime

class ShortenRequest(BaseModel):
    original_url: HttpUrl
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None
    
    @validator('original_url')
    def validate_url(cls, v):
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URLはhttp://またはhttps://で始まる必要があります')
        return v

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    qr_code_url: str
    created_at: str
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

class ClickData(BaseModel):
    id: int
    ip_address: str
    user_agent: str
    referrer: str
    source: str
    clicked_at: datetime

class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    unique_visitors: int
    qr_clicks: int
    click_data: List[ClickData]

class ExportRequest(BaseModel):
    short_codes: List[str]
    format: str = "json"

class BulkItem(BaseModel):
    url: HttpUrl
    custom_name: Optional[str] = None

class BulkRequest(BaseModel):
    urls: List[BulkItem]
    campaign_name: Optional[str] = None

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

# 追加するクラス
class AnalyticsData(BaseModel):
    short_code: str
    total_clicks: int
    unique_visitors: int
    qr_clicks: int
    last_clicked: Optional[datetime] = None

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
