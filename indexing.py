import sqlite3

conn = sqlite3.connect("torob.db")
cursor = conn.cursor()

print("در حال ساخت ایندکس‌های سریع...")
# ایندکس روی عنوان و برند محصولات
cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_title ON products(persian_title);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_name);")

# ایندکس روی آفرهای فروشگاه‌ها
cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_product_id ON offers(product_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_price ON offers(price_toman);")

# ایندکس روی فروشگاه‌ها
cursor.execute("CREATE INDEX IF NOT EXISTS idx_shops_id ON shops(shop_id);")

conn.commit()
conn.close()
print("ایندکس‌گذاری کامل شد! سرعت جست‌وجو آنی شد.")
