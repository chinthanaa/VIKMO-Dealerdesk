# Design Decisions — VIKMO DealerDesk

## 1. Framework and Architecture

Django is used to implement the backend API. The application separates configuration, URL routing, data models, and request handling. API endpoints are implemented in `core/views.py`, while database entities are defined in `core/models.py`. This structure keeps request validation and business logic organized.

**Code references:** `dealerdesk/settings.py`, `dealerdesk/urls.py`, `core/models.py`, `core/views.py`.

## 2. Database

PostgreSQL is used as the relational database, with Django ORM handling database operations and model relationships. The product and dealer seed command supports repeatable initialization of the catalogue and dealer data.

**Code references:** `dealerdesk/settings.py`, `core/models.py`, `core/management/commands/seed_data.py`.

## 3. Data Validation and Error Handling

Incoming JSON requests are validated before database changes are performed. The API checks required fields, product SKUs, quantities, and other request values. Errors use a consistent JSON structure containing an error code, message, and details where applicable.

**Code references:** `core/views.py` — `read_json()`, `error_response()`, `dealers()`, and `orders()`.

## 4. Transaction Safety

Database transactions are used for operations that involve multiple related changes. Order creation groups order and order-item creation inside a transaction. Row-level locking is used when retrieving products for order creation to reduce the risk of concurrent modifications.

**Code references:** `core/views.py` — `orders()` and `transaction.atomic()`.

## 5. API Design and Order Lifecycle

The API uses HTTP methods according to the operation, including GET for retrieving data, POST for creating records, PUT for inventory updates, and order actions for lifecycle transitions. Newly created orders start in `DRAFT` status. The order response includes the order number, dealer ID, status, item-level amounts, subtotal, tax total, grand total, and timestamps.

**Code references:** `core/views.py` — `products()`, `dealers()`, `inventory()`, `orders()`, `order_json()`, and `change_order_status()`.

## 6. Supplier Integration

Supplier synchronization uses a configurable API URL and API key. The implementation supports paginated retrieval, retry handling for temporary failures, and reporting of created, updated, unchanged, and rejected records. The mock supplier test completed successfully, returning four pages and handling invalid supplier items. A second synchronization produced no additional product creations or updates in the tested dataset.

**Code references:** `core/views.py` — supplier synchronization endpoint and its helper functions; supplier configuration in `dealerdesk/settings.py`.

## 7. Configuration and Secrets

Environment variables are used for environment-specific configuration, including database and supplier settings. Secret values should be kept in local environment files and excluded from version control. An example environment file should contain placeholders rather than real credentials.

**Code references:** `dealerdesk/settings.py`, `.env.example`, `.gitignore`.

## 8. Testing and Verification

The provided Django smoke test was run against the local application with the supplier mock service available. The final recorded run passed all nine checks covering health, products, dealers, inventory, order creation, validation, order lifecycle, and supplier-sync response structure.

The smoke test verifies contract basics; it does not guarantee that all hidden evaluation requirements, concurrency cases, or failure scenarios are satisfied.

**Verification command:**
`python smoke_test.py --base-url http://127.0.0.1:8000 --track django`

**Code references:** `smoke_test.py`, `core/views.py`, and `core/models.py`.