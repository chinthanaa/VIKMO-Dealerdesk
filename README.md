# VIKMO DealerDesk

**Track: django**

A Django and PostgreSQL backend for managing a motorcycle and car parts distributor's catalogue, dealers, orders, and supplier integration.

## Implemented Components

- Product catalogue and dealer APIs
- Draft order creation and retrieval
- Order validation and lifecycle handling
- Inventory and GST calculations
- Supplier catalogue synchronization with pagination and retry handling
- Consistent JSON API error responses

**Known limitation:** Supplier synchronization currently returns HTTP 502 during testing and needs further verification.

## Technology Stack

- Python 3.11+
- Django 5.2
- PostgreSQL
- Django ORM
- Requests

## Project Structure

- `core/` — models, API views, URLs, and management commands
- `dealerdesk/` — Django project configuration
- `data/` — catalogue and supporting CSV datasets
- `supplier_mock/` — supplier API mock
- `ml/` — ML-related documentation
- `smoke_test.py` — API smoke tests
- `API_CONTRACT.md` — API specification
- `DECISIONS.md` — design decisions

## Setup

1. Install Python 3.11+ and PostgreSQL.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the required environment variables using `.env.example` as a reference: `DATABASE_URL`, `SUPPLIER_API_URL`, and `SUPPLIER_API_KEY`.
4. Apply migrations:

   ```bash
   python manage.py migrate --noinput
   ```

5. Seed the database:

   ```bash
   python manage.py seed_data
   ```

6. Start the server:

   ```bash
   python manage.py runserver
   ```

## Testing

Run the Django system check:

```bash
python manage.py check
```

Run the Django-track smoke test against a running, freshly seeded database:

```bash
python smoke_test.py --base-url http://127.0.0.1:8000 --track django
```

Start the supplier mock with:

```bash
python supplier_mock/mock_supplier.py
```

## Documentation

See `API_CONTRACT.md` for endpoint specifications and `DECISIONS.md` for design decisions.

## Walkthrough Video

Add your unlisted YouTube, Loom, or Google Drive walkthrough link here after recording the five-minute video.

## Known Issues

Supplier synchronization remains unverified because it returns HTTP 502 during testing. This should be investigated further.
