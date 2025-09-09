# main.py で直接必要なクラスを定義
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 簡単な仮定義
class AnalyticsData(BaseModel):
    pass

class ClickDetail(BaseModel):
    pass

class SystemStats(BaseModel):
    pass

class ErrorResponse(BaseModel):
    error: str

# 既存のインポートはそのまま
from models import ShortenRequest, ShortenResponse, BulkRequest, BulkResponse
