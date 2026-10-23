#!/usr/bin/env python3
"""Stream the Torob CSV exports into SQLite using bounded batches."""
from __future__ import annotations
import argparse, csv, sqlite3, zipfile
from pathlib import Path
from typing import Iterable

SCHEMAS = {
    "shops": ("shop_id", "address", "category_names", "contacts", "instagram", "lat", "location_label", "lon", "name", "payment_options", "supports_fast_delivery", "website_url", "weekly_hours"),
    "products": ("product_id", "brand_name", "category_name", "image_urls", "model", "persian_title", "specs"),
    "offers": ("offer_id", "description", "last_price_changed_at", "price_toman", "product_id", "seller_title", "shop_id", "warranty"),
}

def batches(rows: Iterable[dict], size: int):
    batch=[]
    for row in rows:
        batch.append(row)
        if len(batch)>=size:
            yield batch
            batch=[]
    if batch: yield batch

def ingest(input_dir: Path, database: Path, batch_size: int=5000):
    if batch_size < 1: raise ValueError("batch-size must be positive")
    input_dir.mkdir(parents=True, exist_ok=True)
    for table in ("products", "offers"):
        archive=input_dir/f"{table}.zip"
        target=input_dir/f"{table}.csv"
        if not target.exists() and archive.is_file():
            with zipfile.ZipFile(archive) as zf:
                member=next((n for n in zf.namelist() if n.endswith(f"{table}.csv")), None)
                if member is None: raise FileNotFoundError(f"{archive} does not contain {table}.csv")
                with zf.open(member) as src, target.open("wb") as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
    missing=[f"{name}.csv" for name in SCHEMAS if not (input_dir/f"{name}.csv").is_file()]
    if missing: raise FileNotFoundError(f"Missing CSV file(s): {', '.join(missing)}")
    database.parent.mkdir(parents=True,exist_ok=True)
    counts={}
    with sqlite3.connect(database) as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.executescript("""
        CREATE TABLE IF NOT EXISTS shops (shop_id TEXT PRIMARY KEY, address TEXT, category_names TEXT, contacts TEXT, instagram TEXT, lat REAL, location_label TEXT, lon REAL, name TEXT, payment_options TEXT, supports_fast_delivery TEXT, website_url TEXT, weekly_hours TEXT);
        CREATE TABLE IF NOT EXISTS products (product_id TEXT PRIMARY KEY, brand_name TEXT, category_name TEXT, image_urls TEXT, model TEXT, persian_title TEXT, specs TEXT);
        CREATE TABLE IF NOT EXISTS offers (offer_id TEXT PRIMARY KEY, description TEXT, last_price_changed_at TEXT, price_toman INTEGER, product_id TEXT, seller_title TEXT, shop_id TEXT, warranty TEXT);
        CREATE INDEX IF NOT EXISTS idx_products_title ON products(persian_title);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_name);
        CREATE INDEX IF NOT EXISTS idx_offers_product_price ON offers(product_id, price_toman);
        CREATE INDEX IF NOT EXISTS idx_offers_shop ON offers(shop_id);
        """)
        for table, columns in SCHEMAS.items():
            source=input_dir/f"{table}.csv"
            sql=f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
            total=0
            with source.open('r',encoding='utf-8-sig',newline='') as fh:
                reader=csv.DictReader(fh)
                absent=set(columns)-set(reader.fieldnames or [])
                if absent: raise ValueError(f"{source} missing columns: {sorted(absent)}")
                for group in batches(reader,batch_size):
                    values=[]
                    for row in group:
                        item=[]
                        for col in columns:
                            val=row.get(col)
                            if val is None or val=="null": val=None
                            elif table=="shops" and col in ("lat","lon"):
                                try: val=float(val)
                                except (TypeError,ValueError): val=None
                            elif table=="offers" and col=="price_toman":
                                try: val=int(float(val))
                                except (TypeError,ValueError): val=None
                            item.append(val)
                        values.append(tuple(item))
                    with con: con.executemany(sql,values)
                    total+=len(values)
            counts[table]=total
    return counts

def main():
    here=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=here/'data',help='Directory containing the three CSV files')
    parser.add_argument('--database',type=Path,default=here/'torob.db')
    parser.add_argument('--batch-size',type=int,default=5000)
    args=parser.parse_args()
    print('Imported rows:',ingest(args.input_dir,args.database,args.batch_size))
    print(f'Database: {args.database.resolve()}')
if __name__=='__main__': main()
