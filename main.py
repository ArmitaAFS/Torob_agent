"""FastAPI backend for the Torob shopping assistant."""
from __future__ import annotations
import math, os, sqlite3
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT=Path(__file__).resolve().parents[2]
DB_PATH=Path(os.getenv("TOROB_DB_PATH",str(PROJECT_ROOT/"torob.db")))
app=FastAPI(title="Torob Shopping Assistant API",version="1.0.0",description="API فارسی جست‌وجو و مقایسه پیشنهادهای خرید")
_origins={x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()}
_origins.update({"http://localhost:3000", "*"})
app.add_middleware(CORSMiddleware,allow_origins=sorted(_origins),allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

from fastapi.responses import JSONResponse
@app.exception_handler(sqlite3.Error)
def database_error_handler(request, exc):
    return JSONResponse(status_code=503,content={"detail":"خطا در دسترسی به پایگاه داده. آماده‌بودن پایگاه داده را بررسی کنید."})

@app.exception_handler(Exception)
def unexpected_error_handler(request, exc):
    return JSONResponse(status_code=500,content={"detail":"خطای داخلی سرور رخ داد."})

STATIC_DIR=Path(__file__).resolve().parent/"static"
app.mount("/static",StaticFiles(directory=STATIC_DIR),name="static")

@app.get("/", tags=["system"], response_class=FileResponse)
def root():
    return FileResponse(STATIC_DIR/"index.html",media_type="text/html")

def connect():
    if not DB_PATH.is_file(): raise HTTPException(status_code=503,detail=f"Database not found: {DB_PATH}. Run scripts/import_data.py first.")
    con=sqlite3.connect(f"file:{DB_PATH}?mode=ro",uri=True,timeout=15)
    con.row_factory=sqlite3.Row
    return con

def dump(rows): return [dict(r) for r in rows]

@app.get('/api/health')
def health():
    with connect() as con:
        counts={t:con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('shops','products','offers')}
    return {"status":"ok","database":str(DB_PATH),"counts":counts}

@app.get('/api/products/search')
def search_products(q:str=Query(...,min_length=1,max_length=160),limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0)):
    terms=[x.strip() for x in q.split() if x.strip()][:8]
    if not terms: return {"query":q,"items":[]}
    where=' AND '.join('(persian_title LIKE ? OR brand_name LIKE ? OR category_name LIKE ? OR model LIKE ?)' for _ in terms)
    args=[]
    for term in terms: args.extend([f'%{term}%']*4)
    with connect() as con:
        rows=con.execute(f'''SELECT p.product_id,p.persian_title,p.brand_name,p.category_name,p.image_urls,p.model,
          MIN(o.price_toman) AS min_price,COUNT(o.offer_id) AS offer_count
          FROM products p LEFT JOIN offers o ON o.product_id=p.product_id
          WHERE {where} GROUP BY p.product_id ORDER BY (min_price IS NULL),min_price LIMIT ? OFFSET ?''',(*args,limit,offset)).fetchall()
    return {"query":q,"items":dump(rows),"limit":limit,"offset":offset}

@app.get('/api/products/{product_id}/offers')
def product_offers(product_id:str,sort:str=Query('price',pattern='^(price|distance)$'),lat:Optional[float]=None,lon:Optional[float]=None):
    with connect() as con:
        product=con.execute('SELECT product_id,persian_title,brand_name,category_name FROM products WHERE product_id=?',(product_id,)).fetchone()
        if not product: raise HTTPException(status_code=404,detail='محصول پیدا نشد')
        rows=dump(con.execute('''SELECT o.offer_id,o.price_toman,o.description,o.last_price_changed_at,o.seller_title,o.warranty,o.shop_id,
        s.name AS shop_name,s.address,s.location_label,s.lat,s.lon,s.contacts,s.website_url
        FROM offers o LEFT JOIN shops s ON s.shop_id=o.shop_id WHERE o.product_id=? AND o.price_toman IS NOT NULL''',(product_id,)).fetchall())
    for r in rows:
        r['distance_km']=None
        if lat is not None and lon is not None and r.get('lat') is not None and r.get('lon') is not None:
            a1,a2=math.radians(lat),math.radians(r['lat']); da=math.radians(r['lat']-lat); dl=math.radians(r['lon']-lon)
            h=math.sin(da/2)**2+math.cos(a1)*math.cos(a2)*math.sin(dl/2)**2
            r['distance_km']=round(6371*2*math.asin(min(1,math.sqrt(h))),2)
    rows.sort(key=lambda r: (r['distance_km'] is None,r['distance_km'] or 0,r['price_toman']) if sort=='distance' else (r['price_toman'],))
    return {"product":dict(product),"offers":rows}

@app.get('/api/stores/{shop_id}')
def store_details(shop_id:str):
    with connect() as con:
        shop=con.execute('SELECT * FROM shops WHERE shop_id=?',(shop_id,)).fetchone()
        if not shop: raise HTTPException(status_code=404,detail='فروشگاه پیدا نشد')
        summary=con.execute('SELECT COUNT(*) offer_count,MIN(price_toman) lowest_price FROM offers WHERE shop_id=?',(shop_id,)).fetchone()
    return {"store":dict(shop),"stats":dict(summary)}

class NeedRequest(BaseModel):
    need:str=Field(min_length=2,max_length=300)
    budget:Optional[int]=Field(default=None,gt=0)
    limit:int=Field(default=10,ge=1,le=30)

@app.post('/api/needs/discover')
def discover_needs(body:NeedRequest):
    # Transparent keyword matching, ranked by price and offer availability.
    words=[w.strip() for w in body.need.split() if len(w.strip())>=2][:8]
    if not words: return {"need":body.need,"recommendations":[],"message":"لطفاً نیازتان را دقیق‌تر توضیح دهید."}
    clauses=[]; params=[]
    for word in words:
        clauses.append('(p.persian_title LIKE ? OR p.brand_name LIKE ? OR p.category_name LIKE ?)')
        params.extend([f'%{word}%']*3)
    sql=f'''SELECT p.product_id,p.persian_title,p.brand_name,p.category_name,MIN(o.price_toman) min_price,COUNT(o.offer_id) offer_count
       FROM products p LEFT JOIN offers o ON o.product_id=p.product_id
       WHERE ({' OR '.join(clauses)})'''
    if body.budget is not None: sql+=' AND (o.price_toman IS NULL OR o.price_toman<=?)'; params.append(body.budget)
    sql+=' GROUP BY p.product_id ORDER BY (min_price IS NULL),min_price DESC,offer_count DESC LIMIT ?'; params.append(body.limit)
    with connect() as con: items=dump(con.execute(sql,params).fetchall())
    return {"need":body.need,"budget":body.budget,"recommendations":items,"message":("بر اساس توضیحات و بودجه‌تان این گزینه‌ها را پیدا کردم." if items else "محصول مناسبی با این عبارت/بودجه پیدا نشد؛ عبارت یا بودجه را تغییر دهید.")}
