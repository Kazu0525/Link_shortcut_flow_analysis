from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import random
import string
import json
import os
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# データベース（メモリ内）
url_db = {}

def generate_code(length=6):
    """ランダムコード生成"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_short_url(original_url, custom_code=None, custom_name=None, campaign=None):
    """短縮URL作成"""
    code = custom_code if custom_code else generate_code()
    
    # 重複チェック
    if code in url_db:
        if custom_code:
            return None, "このコードは既に使用されています"
        else:
            while code in url_db:
                code = generate_code()
    
    url_db[code] = {
        "original_url": original_url,
        "custom_name": custom_name,
        "campaign": campaign,
        "created_at": datetime.now().isoformat(),
        "clicks": 0
    }
    
    return code, None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ホームページ - 表形式スプレッドシートUI"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/bulk-generate")
async def bulk_generate(data: str = Form(...)):
    """一括URL生成API"""
    try:
        request_data = json.loads(data)
        results = []
        
        for item in request_data:
            url = item.get('url', '').strip()
            custom_code = item.get('custom_code', '').strip()
            custom_name = item.get('custom_name', '').strip()
            campaign = item.get('campaign', '').strip()
            original_row = item.get('original_row', 0)
            
            if not url:
                continue
                
            if not url.startswith(('http://', 'https://')):
                results.append({
                    "url": url,
                    "success": False,
                    "error": "無効なURL形式",
                    "original_row": original_row
                })
                continue
            
            # 短縮URL生成
            code, error = create_short_url(
                original_url=url,
                custom_code=custom_code if custom_code else None,
                custom_name=custom_name if custom_name else None,
                campaign=campaign if campaign else None
            )
            
            if error:
                results.append({
                    "url": url,
                    "success": False,
                    "error": error,
                    "original_row": original_row
                })
            else:
                base_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
                results.append({
                    "url": url,
                    "success": True,
                    "short_url": f"{base_url}/s/{code}",
                    "short_code": code,
                    "custom_name": custom_name,
                    "campaign": campaign,
                    "original_row": original_row
                })
        
        return JSONResponse({"results": results})
        
    except Exception as e:
        return JSONResponse(
            {"error": f"処理エラー: {str(e)}"},
            status_code=400
        )

@app.get("/s/{code}")
async def redirect_url(code: str):
    """短縮URLリダイレクト"""
    if code in url_db:
        url_db[code]["clicks"] += 1
        return RedirectResponse(url_db[code]["original_url"])
    return HTMLResponse("URL not found", status_code=404)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """管理画面"""
    campaign_stats = {}
    for code, data in url_db.items():
        campaign = data.get("campaign", "未分類")
        if campaign not in campaign_stats:
            campaign_stats[campaign] = {"count": 0, "clicks": 0}
        campaign_stats[campaign]["count"] += 1
        campaign_stats[campaign]["clicks"] += data["clicks"]
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "url_db": url_db,
        "campaign_stats": campaign_stats
    })

@app.get("/health")
async def health():
    return {"status": "healthy", "urls": len(url_db)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
