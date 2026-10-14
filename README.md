# VIKMO DealerDesk

**Track: Django**

A Django and PostgreSQL backend for managing a motorcycle and car parts distributor's catalogue, dealers, orders, inventory, and supplier integration.

## Implemented Components

- Product catalogue and dealer APIs
- Draft order creation and retrieval
- Order validation and lifecycle handling
- Inventory management and GST calculations
- Supplier catalogue synchronization with pagination and retry handling
- Consistent JSON API error responses

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
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the required environment variables using `.env.example` as a reference:

   - `DATABASE_URL`
   - `SUPPLIER_API_URL`
   - `SUPPLIER_API_KEY`

   Use your own local values. Do not commit real credentials.

5. Apply migrations:

   ```bash
   python manage.py migrate
   ```

6. Seed the database:

   ```bash
   python manage.py seed_data
   ```

   The seed command can be run again to verify that seeding does not duplicate the seeded catalogue or dealer records.

## Run the Application

Start the supplier mock in one terminal:

```bash
python supplier_mock/mock_supplier.py
```

Configure `SUPPLIER_API_URL` and `SUPPLIER_API_KEY` to match the mock service's printed values.

Start Django in another terminal:

```bash
python manage.py runserver
```

## Testing

Run the Django system check:

```bash
python manage.py check
```

With Django and the supplier mock running, execute:

```bash
python smoke_test.py --base-url http://127.0.0.1:8000 --track django
```

The final recorded smoke-test run passed all 9 checks. This verifies the tested API basics, but does not guarantee that every hidden evaluation requirement has been satisfied.

## Documentation

See `API_CONTRACT.md` for endpoint specifications and `DECISIONS.md` for design decisions.

## Walkthrough Video

**Video link:** Add the URL to your five-minute code walkthrough here after uploading it.

