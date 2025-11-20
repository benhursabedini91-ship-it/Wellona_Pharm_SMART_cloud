# Wellona Pharm SMART Cloud - Flask API Documentation

## Overview

This is a clean Flask backend API skeleton for **Porosi AI** (Orders) and **Faktura AI** (Invoice Import), aligned with the existing `wphAI` and `WPH_EFaktura_Package` structure.

## Project Structure

```
.
├── app.py                          # Main Flask entrypoint
├── .env.example                    # Environment variables template
├── requirements.txt                # Python dependencies
├── app/
│   ├── __init__.py                # Flask app factory with create_app()
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py                # API key authentication middleware
│   ├── utils/
│   │   ├── __init__.py
│   │   └── response.py            # Standardized response helpers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orders_service.py      # Porosi AI business logic
│   │   └── faktura_service.py     # Faktura AI business logic
│   └── routes/
│       ├── __init__.py
│       ├── orders_api.py          # Orders API endpoints (/api)
│       └── faktura_api.py         # Faktura AI endpoints (/faktura-ai)
```

## Setup

### 1. Create Environment Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Flask Configuration
FLASK_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8055

# API Authentication
API_KEY=f7b40af0-9689-4872-8d59-4779f7961175

# PostgreSQL Configuration
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB=wph_ai
PG_USER=postgres
PG_PASSWORD=your-password-here

# CORS Configuration
CORS_ORIGIN_DEV=http://localhost:3000
CORS_ORIGIN_PROD=https://ai.wellonapharm.com

# Optional: Foreign Data Wrapper
WPH_USE_FDW=0
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python app.py
```

The server will start on `http://0.0.0.0:8055` (or the port specified in `.env`).

## API Endpoints

### Health Check (No Authentication)

**GET** `/health`

Returns basic status information.

**Example:**
```bash
curl http://localhost:8055/health
```

**Response:**
```json
{
  "status": "ok",
  "message": "Wellona Pharm SMART Cloud API is running",
  "environment": "development"
}
```

---

### Orders API (Porosi AI)

All `/api/*` endpoints require the `X-API-Key` header.

#### Get Orders

**GET** `/api/orders`

Query Parameters:
- `limit` (optional): Maximum number of orders (default: 100, max: 5000)
- `offset` (optional): Number of orders to skip (default: 0)
- `urgent_only` (optional): Filter urgent orders only (true/false, default: false)

**Example:**
```bash
curl -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  "http://localhost:8055/api/orders?limit=10&urgent_only=true"
```

**Response:**
```json
{
  "status": "ok",
  "message": "Orders retrieved successfully",
  "data": {
    "items": [
      {
        "sifra": "ART001",
        "name": "Aspirin 100mg",
        "stock": 50,
        "avg_daily": 10.5,
        "cover_days": 4.76,
        "min_zaliha": 100,
        "qty_to_order": 150,
        "urgent_flag": true
      }
    ],
    "total": 2,
    "limit": 10,
    "offset": 0,
    "filters": {
      "urgent_only": true
    }
  }
}
```

#### Export Orders

**GET** `/api/orders/export`

Query Parameters:
- `format` (optional): Export format (csv, xlsx) - default: csv
- `limit` (optional): Maximum number of orders (default: 100, max: 5000)
- `urgent_only` (optional): Filter urgent orders only (true/false, default: false)

**Example:**
```bash
curl -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  "http://localhost:8055/api/orders/export?format=csv" \
  -o orders.csv
```

**Response:** CSV file download

#### Approve Orders

**POST** `/api/orders/approve`

Request Body:
```json
{
  "order_ids": ["order1", "order2", "order3"]
}
```

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  -H "Content-Type: application/json" \
  -d '{"order_ids": ["order1", "order2", "order3"]}' \
  http://localhost:8055/api/orders/approve
```

**Response:**
```json
{
  "status": "ok",
  "message": "Orders approval completed",
  "data": {
    "approved": 3,
    "failed": 0,
    "order_ids": ["order1", "order2", "order3"],
    "timestamp": "2025-01-15T10:30:00.123456"
  }
}
```

---

### Faktura AI API (Invoice Import)

All `/faktura-ai/*` endpoints require the `X-API-Key` header.

#### Import CSV

**POST** `/faktura-ai/import-csv`

Form Data:
- `file` (required): CSV file
- `mode` (optional): `dry_run` or `commit` (default: `dry_run`)

**Example (Dry Run):**
```bash
curl -X POST \
  -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  -F "file=@invoices.csv" \
  -F "mode=dry_run" \
  http://localhost:8055/faktura-ai/import-csv
```

**Example (Commit):**
```bash
curl -X POST \
  -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  -F "file=@invoices.csv" \
  -F "mode=commit" \
  http://localhost:8055/faktura-ai/import-csv
```

**Response (Dry Run):**
```json
{
  "status": "ok",
  "message": "CSV import simulated",
  "data": {
    "status": "ok",
    "message": "CSV import simulated",
    "mode": "dry_run",
    "totals": {
      "processed": 3,
      "warnings": 0
    },
    "items": [
      {
        "line": 1,
        "sifra": "ART001",
        "kolicina": 100,
        "status": "pending"
      }
    ],
    "warnings": []
  }
}
```

#### Parse XML Invoice

**POST** `/faktura-ai/import-xml/parse`

Form Data:
- `file` (required): XML file (Sopharma/UBL format)

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  -F "file=@invoice.xml" \
  http://localhost:8055/faktura-ai/import-xml/parse
```

**Response:**
```json
{
  "status": "ok",
  "message": "XML parsed successfully",
  "data": {
    "status": "ok",
    "message": "XML parsed successfully",
    "header": {
      "invoice_no": "INV-2025-001",
      "supplier": "Sopharma AD",
      "invoice_date": "2025-01-15",
      "total_neto": 5000.0,
      "cash_discount": 250.0,
      "payable_amount": 4750.0,
      "due_date": "2025-02-15"
    },
    "items": [
      {
        "sifra": "SOPH001",
        "name": "Medication A",
        "quantity": 100,
        "price": 25.0,
        "total": 2500.0
      }
    ],
    "totals": {
      "items_count": 2,
      "total_quantity": 150,
      "total_amount": 5000.0
    }
  }
}
```

#### Commit XML Invoice

**POST** `/faktura-ai/import-xml/commit`

Form Data:
- `file` (required): XML file (Sopharma/UBL format)

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  -F "file=@invoice.xml" \
  http://localhost:8055/faktura-ai/import-xml/commit
```

**Response:**
```json
{
  "status": "ok",
  "message": "XML invoice committed successfully",
  "data": {
    "status": "ok",
    "message": "XML invoice committed successfully",
    "invoice_no": "INV-2025-001",
    "totals": {
      "items_inserted": 2,
      "total_amount": 5000.0
    },
    "timestamp": "2025-01-15T10:30:00.123456"
  }
}
```

---

## Authentication

All API endpoints (except `/health`) require the `X-API-Key` header for authentication.

**Example:**
```bash
curl -H "X-API-Key: f7b40af0-9689-4872-8d59-4779f7961175" \
  http://localhost:8055/api/orders
```

**Error Response (401 Unauthorized):**
```json
{
  "status": "error",
  "message": "Unauthorized",
  "code": "INVALID_API_KEY"
}
```

---

## CORS Configuration

CORS is configured to allow requests from:
- **Development:** `http://localhost:3000`
- **Production:** `https://ai.wellonapharm.com`

Configure these in your `.env` file:
```env
CORS_ORIGIN_DEV=http://localhost:3000
CORS_ORIGIN_PROD=https://ai.wellonapharm.com
```

---

## Response Format

All API responses follow a standardized format:

### Success Response
```json
{
  "status": "ok",
  "message": "Success message",
  "data": { /* response data */ }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error message",
  "code": "ERROR_CODE"
}
```

---

## Next Steps

### Integration with Existing Systems

The current implementation uses mock data. To integrate with the existing `wphAI` and `WPH_EFaktura_Package`:

1. **Orders Service (`app/services/orders_service.py`):**
   - Connect to the `wph_ai` database
   - Use the SQL queries from `wphAI/web_modern/app.py`
   - Integrate with `ops.article_status` and `ops.article_urgency` tables

2. **Faktura Service (`app/services/faktura_service.py`):**
   - Integrate with `app/modules/faktura_ai/sopharma_to_erp.py`
   - Use the CSV and XML parsing logic from `WPH_EFaktura_Package`
   - Connect to the database for commit operations

### Development Tips

- Use `FLASK_ENV=development` for debugging
- Set `FLASK_ENV=production` for production deployment
- Consider using a production WSGI server (e.g., Gunicorn, uWSGI) for production
- Monitor logs for API usage and errors
- Rotate API keys regularly for security

---

## Dependencies

- **Flask 2.3.3** - Web framework
- **Flask-CORS 4.0.0** - CORS support
- **python-dotenv 1.0.0** - Environment variable management
- **psycopg2-binary 2.9.9** - PostgreSQL adapter
- **SQLAlchemy 2.0.23** - Database ORM

---

## Support

For issues or questions, refer to the existing documentation:
- `wphAI/` - Core AI + DB logic for orders
- `WPH_EFaktura_Package/` - eFaktura integration tools
- `docs/` - Additional documentation

---

## License

This project is part of the Wellona Pharm SMART Cloud system.
