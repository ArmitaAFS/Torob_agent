 # Torob Tehran In-Person Shopping Assistant

A smart shopping assistant for finding products and nearby physical stores in Tehran using Torob datasets.

The system helps users search for products, compare available offers, and find the most suitable nearby shops based on price, location, availability, and delivery options.

## Features

- Persian RTL user interface
- Product and shop search
- Product offer comparison
- Nearby shop recommendations
- Distance calculation using shop coordinates
- Price and seller comparison
- Support for Persian product names and categories
- FastAPI backend
- Simple HTML, CSS, and JavaScript frontend
- No external frontend package installation required

## Dataset

The project uses three CSV datasets:

- `shops.csv`: Information about 6,476 shops
- `products.csv`: Information about 225,903 products
- `offers.csv`: Information about 331,506 product offers

The datasets include information such as:

- Product names and brands
- Categories and specifications
- Prices
- Seller names
- Shop addresses
- Geographic coordinates
- Payment methods
- Warranty information
- Delivery support

## How It Works

1. The user searches for a product in Persian or English.
2. The backend searches the product and offer data.
3. Available sellers and prices are collected.
4. Nearby physical shops are ranked using geographic distance.
5. The assistant presents the most relevant results to the user.

The distance between the user and each shop is calculated using the Haversine formula:

```text
distance = 2R × arcsin(
  √(
    sin²((lat₂ - lat₁) / 2) +
    cos(lat₁) × cos(lat₂) × sin²((lon₂ - lon₁) / 2)
  )
)
```

## Technology Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- HTML5
- CSS3
- JavaScript
- RTL Persian interface

## Project Structure

```text
torob-shopping-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── static/
│   │       └── index.html
│   └── Dockerfile
├── data/
│   ├── shops.csv
│   ├── products.zip
│   └── offers.zip
├── scripts/
│   └── import_data.py
├── requirements.txt
└── README.md
```

## Main API Endpoints

```text
GET /
GET /docs
GET /api/search
GET /api/offers/{offer_id}
GET /api/agent/discover
```

The `/docs` endpoint provides an interactive API documentation page.

## Data Attribution

The application is based on Torob product, offer, and shop datasets. The original dataset structure and field names are preserved where possible.
