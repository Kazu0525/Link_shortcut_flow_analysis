from fastapi import APIRouter, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any
import sqlite3

# 絶対インポートに変更
import config
from models import BulkRequest, BulkResponse, BulkResponseItem, ShortenRequest
from utils import get_db_connection, generate_short_code, validate_url, clean_url
from routes.shorten import generate_qr_code

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/bulk", response_class=HTMLResponse)
async def bulk_page(request: Request):
    """一括生成ページの表示"""
    try:
        return templates.TemplateResponse("bulk.html", {
            "request": request,
            "base_url": config.BASE_URL
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括生成ページの表示でエラーが発生しました: {str(e)}")

@router.post("/api/bulk", response_model=BulkResponse)
async def bulk_shorten_urls(request: BulkRequest):
    """一括URL短縮APIエンドポイント"""
    try:
        if len(request.urls) > 100:
            raise HTTPException(status_code=400, detail="一度に処理できるURLは100件までです")
        
        results = []
        success_count = 0
        failed_count = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for item in request.urls:
                try:
                    # URL検証
                    if not validate_url(str(item.url)):
                        results.append(BulkResponseItem(
                            original_url=str(item.url),
                            short_code="",
                            short_url="",
                            qr_code_url="",
                            custom_name=item.custom_name,
                            success=False,
                            error_message="無効なURLです"
                        ))
                        failed_count += 1
                        continue
                    
                    # 短縮コード生成
                    short_code = await generate_unique_short_code_bulk(cursor)
                    
                    # QRコード生成
                    qr_code_data = generate_qr_code(f"{config.BASE_URL}/{short_code}")
                    
                    # データベースに保存
                    cursor.execute("""
                        INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        short_code,
                        clean_url(str(item.url)),
                        item.custom_name,
                        request.campaign_name,
                        datetime.now().isoformat()
                    ))
                    
                    results.append(BulkResponseItem(
                        original_url=str(item.url),
                        short_code=short_code,
                        short_url=f"{config.BASE_URL}/{short_code}",
                        qr_code_url=qr_code_data,
                        custom_name=item.custom_name,
                        success=True
                    ))
                    success_count += 1
                    
                except Exception as item_error:
                    results.append(BulkResponseItem(
                        original_url=str(item.url),
                        short_code="",
                        short_url="",
                        qr_code_url="",
                        custom_name=item.custom_name,
                        success=False,
                        error_message=str(item_error)
                    ))
                    failed_count += 1
            
            conn.commit()
            
        finally:
            conn.close()
        
        return BulkResponse(
            results=results,
            total_count=len(request.urls),
            success_count=success_count,
            failed_count=failed_count,
            campaign_name=request.campaign_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括処理でエラーが発生しました: {str(e)}")

@router.post("/api/bulk/upload")
async def bulk_upload_file(
    file: UploadFile = File(...),
    campaign_name: str = Form(None)
):
    """ファイルアップロードによる一括処理"""
    try:
        # ファイル形式チェック
        if not file.filename.endswith(('.csv', '.json', '.txt')):
            raise HTTPException(status_code=400, detail="CSVまたはJSONファイルをアップロードしてください")
        
        # ファイル内容を読み取り
        content = await file.read()
        content_str = content.decode('utf-8')
        
        urls_data = []
        
        if file.filename.endswith('.csv'):
            # CSV処理
            csv_reader = csv.DictReader(io.StringIO(content_str))
            for row in csv_reader:
                url = row.get('url', '').strip()
                custom_name = row.get('custom_name', '').strip() or None
                
                if url:
                    urls_data.append({
                        "url": url,
                        "custom_name": custom_name
                    })
        
        elif file.filename.endswith('.json'):
            # JSON処理
            try:
                json_data = json.loads(content_str)
                if isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and 'url' in item:
                            urls_data.append({
                                "url": item['url'],
                                "custom_name": item.get('custom_name')
                            })
                        elif isinstance(item, str):
                            urls_data.append({
                                "url": item,
                                "custom_name": None
                            })
                elif isinstance(json_data, dict) and 'urls' in json_data:
                    urls_data = json_data['urls']
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="無効なJSON形式です")
        
        elif file.filename.endswith('.txt'):
            # テキストファイル処理（1行1URL）
            for line in content_str.strip().split('\n'):
                url = line.strip()
                if url:
                    urls_data.append({
                        "url": url,
                        "custom_name": None
                    })
        
        if not urls_data:
            raise HTTPException(status_code=400, detail="有効なURLが見つかりませんでした")
        
        if len(urls_data) > 500:
            raise HTTPException(status_code=400, detail="一度にアップロードできるURLは500件までです")
        
        # BulkRequestオブジェクトを作成
        bulk_request = BulkRequest(
            urls=[{"url": item["url"], "custom_name": item["custom_name"]} for item in urls_data],
            campaign_name=campaign_name
        )
        
        # 一括処理実行
        result = await bulk_shorten_urls(bulk_request)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルアップロード処理でエラーが発生しました: {str(e)}")

async def generate_unique_short_code_bulk(cursor, length=6):
    """バルク処理用の重複しない短縮コードを生成"""
    import string
    import random
    
    chars = string.ascii_letters + string.digits
    max_attempts = 50
    
    for _ in range(max_attempts):
        code = ''.join(random.choices(chars, k=length))
        
        # データベースで重複チェック
        cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,))
        exists = cursor.fetchone()
        
        if not exists:
            return code
    
    raise HTTPException(status_code=500, detail="短縮コードの生成に失敗しました")

@router.get("/api/bulk/template")
async def download_template(format: str = "csv"):
    """アップロード用テンプレートファイルのダウンロード"""
    try:
        if format == "csv":
            csv_content = "url,custom_name\nhttps://example.com,Example Site\nhttps://google.com,Google Search\n"
            
            return JSONResponse({
                "filename": "bulk_upload_template.csv",
                "content": csv_content,
                "content_type": "text/csv"
            })
        
        elif format == "json":
            json_content = json.dumps({
                "urls": [
                    {"url": "https://example.com", "custom_name": "Example Site"},
                    {"url": "https://google.com", "custom_name": "Google Search"}
                ]
            }, indent=2)
            
            return JSONResponse({
                "filename": "bulk_upload_template.json",
                "content": json_content,
                "content_type": "application/json"
            })
        
        else:
            raise HTTPException(status_code=400, detail="サポートされていない形式です")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"テンプレート生成でエラーが発生しました: {str(e)}")

@router.get("/api/bulk/campaigns")
async def get_campaigns():
    """既存のキャンペーン一覧を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                campaign_name,
                COUNT(*) as url_count,
                SUM(
                    (SELECT COUNT(*) FROM clicks WHERE url_id = urls.id)
                ) as total_clicks
            FROM urls 
            WHERE campaign_name IS NOT NULL AND campaign_name != ''
            GROUP BY campaign_name
            ORDER BY url_count DESC
        """)
        
        campaigns = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return JSONResponse({
            "campaigns": campaigns
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンペーン一覧の取得でエラーが発生しました: {str(e)}")

@router.get("/api/bulk/campaign/{campaign_name}")
async def get_campaign_urls(campaign_name: str):
    """指定したキャンペーンのURL一覧を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.created_at,
                COUNT(c.id) as clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.campaign_name = ? AND u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """, (campaign_name,))
        
        urls = [dict(row) for row in cursor.fetchall()]
        
        # キャンペーン全体の統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_urls,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.campaign_name = ? AND u.is_active = 1
        """, (campaign_name,))
        
        campaign_stats = dict(cursor.fetchone())
        conn.close()
        
        return JSONResponse({
            "campaign_name": campaign_name,
            "stats": campaign_stats,
            "urls": urls
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンペーンURL一覧の取得でエラーが発生しました: {str(e)}")

@router.delete("/api/bulk/campaign/{campaign_name}")
async def delete_campaign(campaign_name: str):
    """キャンペーン全体を削除（論理削除）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # キャンペーンのURLを無効化
        cursor.execute("""
            UPDATE urls 
            SET is_active = 0
            WHERE campaign_name = ?
        """, (campaign_name,))
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "message": f"キャンペーン '{campaign_name}' のURL {deleted_count}件を削除しました",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンペーン削除でエラーが発生しました: {str(e)}")
