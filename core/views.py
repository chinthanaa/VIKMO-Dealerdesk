import os
import json
import requests
import time
from datetime import timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Dealer, Order, OrderItem

def health(request):
    return JsonResponse({"status": "ok"})


def error_response(code, message, status, details=None):
    return JsonResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            }
        },
        status=status,
    )


def read_json(request):
    try:
        data = json.loads(request.body or b"{}")
        if not isinstance(data, dict):
            raise ValueError
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None, error_response(
            "VALIDATION_ERROR", "Request body must be a JSON object.", 400
        )


def product_json(product):
    return {
        "sku": product.sku,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "vehicle_fitment": product.vehicle_fitment,
        "price": f"{product.price:.2f}",
        "stock": product.stock,
        "description": product.description,
    }


def dealer_json(dealer):
    return {
        "id": dealer.id,
        "dealer_code": dealer.dealer_code,
        "name": dealer.name,
        "city": dealer.city,
        "phone": dealer.phone,
        "email": dealer.email,
        "gstin": dealer.gstin,
        "credit_limit": f"{dealer.credit_limit:.2f}",
    }


def paginated(request, queryset, serializer):
    try:
        page = int(request.GET.get("page", "1"))
        page_size = min(int(request.GET.get("page_size", "20")), 100)
        if page < 1 or page_size < 1:
            raise ValueError
    except (ValueError, TypeError):
        return error_response(
            "VALIDATION_ERROR", "Invalid pagination parameters.", 400
        )

    count = queryset.count()
    start = (page - 1) * page_size
    results = [serializer(obj) for obj in queryset[start:start + page_size]]
    base = request.path
    query = request.GET.copy()
    query["page_size"] = str(page_size)

    next_url = None
    previous_url = None
    if start + page_size < count:
        query["page"] = str(page + 1)
        next_url = f"{base}?{query.urlencode()}"
    if page > 1 and start < count:
        query["page"] = str(page - 1)
        previous_url = f"{base}?{query.urlencode()}"

    return JsonResponse({
        "count": count,
        "next": next_url,
        "previous": previous_url,
        "results": results,
    })


@require_http_methods(["GET", "POST"])
def products(request):
    if request.method == "GET":
        qs = Product.objects.all().order_by("sku")
        search = request.GET.get("search", "").strip()
        category = request.GET.get("category", "").strip()
        vehicle = request.GET.get("vehicle", "").strip()
        if search:
            qs = qs.filter(
                Q(sku__icontains=search)
                | Q(name__icontains=search)
                | Q(brand__icontains=search)
            )
        if category:
            qs = qs.filter(category=category)
        if vehicle:
            qs = qs.filter(vehicle_fitment__icontains=vehicle)
        return paginated(request, qs, product_json)

    data, err = read_json(request)
    if err:
        return err
    try:
        sku = str(data.get("sku", "")).strip()
        name = str(data.get("name", "")).strip()
        price = Decimal(str(data.get("price", "")))
        if not sku or not name or not price.is_finite() or price <= 0:
            raise ValueError
        if price.as_tuple().exponent < -2:
            raise ValueError
    except (ValueError, InvalidOperation, TypeError):
        return error_response(
            "VALIDATION_ERROR",
            "sku, name and a positive price with at most 2 decimals are required.",
            400,
        )

    if Product.objects.filter(sku=sku).exists():
        return error_response("DUPLICATE", "Product SKU already exists.", 409)

    try:
        with transaction.atomic():
            product = Product.objects.create(
                sku=sku,
                name=name,
                category=str(data.get("category", "")),
                brand=str(data.get("brand", "")),
                vehicle_fitment=str(data.get("vehicle_fitment", "")),
                description=str(data.get("description", "")),
                price=price,
                stock=0,
            )
    except IntegrityError:
        return error_response("DUPLICATE", "Product SKU already exists.", 409)
    return JsonResponse(product_json(product), status=201)


@require_http_methods(["GET", "PATCH"])
def product_detail(request, sku):
    try:
        product = Product.objects.get(sku=sku)
    except Product.DoesNotExist:
        return error_response("NOT_FOUND", "Product not found.", 404)

    if request.method == "GET":
        return JsonResponse(product_json(product))

    data, err = read_json(request)
    if err:
        return err
    if "sku" in data and data["sku"] != product.sku:
        return error_response("VALIDATION_ERROR", "SKU cannot be changed.", 400)

    for field in ("name", "category", "brand", "vehicle_fitment", "description"):
        if field in data:
            setattr(product, field, str(data[field]))
    if "price" in data:
        try:
            price = Decimal(str(data["price"]))
            if not price.is_finite() or price <= 0 or price.as_tuple().exponent < -2:
                raise ValueError
            product.price = price
        except (ValueError, InvalidOperation, TypeError):
            return error_response("VALIDATION_ERROR", "Invalid price.", 400)
    product.save()
    return JsonResponse(product_json(product))

@csrf_exempt
@require_http_methods(["PUT"])
def inventory(request, sku):
    try:
        product = Product.objects.get(sku=sku)
    except Product.DoesNotExist:
        return error_response("NOT_FOUND", "Product not found.", 404)

    data, err = read_json(request)
    if err:
        return err
    quantity = data.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        return error_response(
            "VALIDATION_ERROR", "quantity must be an integer >= 0.", 400
        )
    product.stock = quantity
    product.save(update_fields=["stock"])
    return JsonResponse({"sku": product.sku, "quantity": product.stock})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def dealers(request):
    if request.method == "GET":
        return paginated(
            request, Dealer.objects.all().order_by("id"), dealer_json
        )

    data, err = read_json(request)
    if err:
        return err
    code = str(data.get("dealer_code", "")).strip()
    name = str(data.get("name", "")).strip()
    if not code or not name:
        return error_response(
            "VALIDATION_ERROR", "dealer_code and name are required.", 400
        )
    if Dealer.objects.filter(dealer_code=code).exists():
        return error_response("DUPLICATE", "Dealer code already exists.", 409)

    try:
        credit_limit = Decimal(str(data.get("credit_limit", "0.00")))
        if not credit_limit.is_finite() or credit_limit < 0:
            raise ValueError
    except (ValueError, InvalidOperation, TypeError):
        return error_response("VALIDATION_ERROR", "Invalid credit_limit.", 400)

    try:
        with transaction.atomic():
            dealer = Dealer.objects.create(
                dealer_code=code,
                name=name,
                city=str(data.get("city", "")),
                phone=str(data.get("phone", "")),
                email=str(data.get("email", "")),
                gstin=str(data.get("gstin", "")),
                credit_limit=credit_limit,
            )
    except IntegrityError:
        return error_response("DUPLICATE", "Dealer code already exists.", 409)
    return JsonResponse(dealer_json(dealer), status=201)


@require_http_methods(["GET"])
def dealer_detail(request, dealer_id):
    try:
        dealer = Dealer.objects.get(id=dealer_id)
    except Dealer.DoesNotExist:
        return error_response("NOT_FOUND", "Dealer not found.", 404)
    return JsonResponse(dealer_json(dealer))
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo


def order_item_json(item):
    return {
        "sku": item.product.sku,
        "name": item.product.name,
        "quantity": item.quantity,
        "unit_price": f"{item.unit_price:.2f}",
        "line_subtotal": f"{item.line_subtotal:.2f}",
        "line_tax": f"{item.line_tax:.2f}",
        "line_total": f"{item.line_total:.2f}",
    }



def order_json(order):
    return {
        "order_number": order.order_number,
        "dealer_id": order.dealer_id,
        "status": order.status,
        "items": [
            order_item_json(item)
            for item in order.items.select_related("product")
        ],
        "subtotal": f"{order.subtotal:.2f}",
        "tax_total": f"{order.tax_total:.2f}",
        "grand_total": f"{order.grand_total:.2f}",
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


def calculate_order_totals(order):
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    for item in order.items.select_related("product"):
        line_subtotal = (item.unit_price * item.quantity).quantize(Decimal("0.01"))
        line_tax = (line_subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
        line_total = line_subtotal + line_tax

        item.line_subtotal = line_subtotal
        item.line_tax = line_tax
        item.line_total = line_total
        item.save(update_fields=["line_subtotal", "line_tax", "line_total"])

        subtotal += line_subtotal
        tax_total += line_tax

    order.subtotal = subtotal
    order.tax_total = tax_total
    order.grand_total = subtotal + tax_total
    order.save(update_fields=["subtotal", "tax_total", "grand_total", "updated_at"])


@csrf_exempt
@require_http_methods(["GET", "POST"])
def orders(request):
    if request.method == "GET":
        qs = Order.objects.select_related("dealer").prefetch_related("items__product").order_by("-created_at")

        if request.GET.get("dealer_id"):
            qs = qs.filter(dealer_id=request.GET["dealer_id"])
        if request.GET.get("status"):
            qs = qs.filter(status=request.GET["status"].upper())

        return paginated(request, qs, order_json)

    data, err = read_json(request)
    if err:
        return err

    dealer_id = data.get("dealer_id")
    items = data.get("items")

    if not dealer_id or not isinstance(items, list) or not items:
        return error_response("VALIDATION_ERROR", "dealer_id and at least one item are required.", 400)

    if not all(isinstance(item, dict) for item in items):
        return error_response("VALIDATION_ERROR", "Each item must be an object.", 400)

    skus = [str(item.get("sku", "")).strip() for item in items]
    if any(not sku for sku in skus) or len(skus) != len(set(skus)):
        return error_response("VALIDATION_ERROR", "Each SKU must be present and unique.", 400)

    try:
        dealer = Dealer.objects.get(id=dealer_id)
    except (Dealer.DoesNotExist, ValueError, TypeError):
        return error_response("NOT_FOUND", "Dealer not found.", 404)

    try:
        with transaction.atomic():
            products = {
                product.sku: product
                for product in Product.objects.select_for_update().filter(sku__in=skus)
            }

            if len(products) != len(skus):
                return error_response("NOT_FOUND", "One or more products were not found.", 404)

            parsed_items = []
            for item in items:
                quantity = item.get("quantity")
                if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                    return error_response("VALIDATION_ERROR", "Quantity must be an integer >= 1.", 400)

                parsed_items.append((products[item["sku"].strip()], quantity))

            day = timezone.localtime(timezone.now(), ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d")
            prefix = f"ORD-{day}-"
            latest = Order.objects.filter(order_number__startswith=prefix).order_by("-order_number").first()
            sequence = int(latest.order_number[-4:]) + 1 if latest else 1
            order_number = f"{prefix}{sequence:04d}"

            order = Order.objects.create(
                order_number=order_number,
                dealer=dealer,
                status="DRAFT",
            )

            for product, quantity in parsed_items:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=product.price,
                )

            calculate_order_totals(order)

    except IntegrityError:
        return error_response("CONFLICT", "Could not create order; please retry.", 409)

    return JsonResponse(order_json(order), status=201)


@require_http_methods(["GET", "PUT"])
def order_detail(request, order_number):
    try:
        order = Order.objects.select_related("dealer").get(order_number=order_number)
    except Order.DoesNotExist:
        return error_response("NOT_FOUND", "Order not found.", 404)

    if request.method == "GET":
        return JsonResponse(order_json(order))

    if order.status != "DRAFT":
        return error_response("ORDER_LOCKED", "Only draft orders can be edited.", 409)

    data, err = read_json(request)
    if err:
        return err

    items = data.get("items")
    if not isinstance(items, list) or not items:
        return error_response("VALIDATION_ERROR", "At least one item is required.", 400)

    skus = [str(item.get("sku", "")).strip() for item in items if isinstance(item, dict)]
    if len(skus) != len(items) or any(not sku for sku in skus) or len(skus) != len(set(skus)):
        return error_response("VALIDATION_ERROR", "Each SKU must be present and unique.", 400)

    with transaction.atomic():
        products = {p.sku: p for p in Product.objects.select_for_update().filter(sku__in=skus)}
        if len(products) != len(skus):
            return error_response("NOT_FOUND", "One or more products were not found.", 404)

        OrderItem.objects.filter(order=order).delete()

        for item in items:
            quantity = item.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                return error_response("VALIDATION_ERROR", "Quantity must be an integer >= 1.", 400)

            product = products[item["sku"].strip()]
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price,
            )

        calculate_order_totals(order)

    return JsonResponse(order_json(order))


def change_order_status(request, order_number, action):
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(order_number=order_number)

            transitions = {
                "confirm": ("DRAFT", "CONFIRMED"),
                "dispatch": ("CONFIRMED", "DISPATCHED"),
                "deliver": ("DISPATCHED", "DELIVERED"),
                "cancel": (("DRAFT", "CONFIRMED"), "CANCELLED"),
            }

            required, new_status = transitions[action]

            allowed = order.status in required if isinstance(required, tuple) else order.status == required
            if not allowed:
                return error_response("INVALID_TRANSITION", "This status transition is not allowed.", 409)

            if action == "confirm":
                short_items = []
                for item in order.items.select_related("product").select_for_update():
                    if item.product.stock < item.quantity:
                        short_items.append({
                            "sku": item.product.sku,
                            "requested": item.quantity,
                            "available": item.product.stock,
                        })

                if short_items:
                    return error_response(
                        "INSUFFICIENT_STOCK",
                        "Insufficient stock for one or more order items.",
                        409,
                        short_items,
                    )

                for item in order.items.select_related("product").select_for_update():
                    product = item.product
                    product.stock -= item.quantity
                    product.save(update_fields=["stock"])

            if action == "cancel" and order.status == "CONFIRMED":
                for item in order.items.select_related("product").select_for_update():
                    product = item.product
                    product.stock += item.quantity
                    product.save(update_fields=["stock"])

            order.status = new_status
            order.save(update_fields=["status", "updated_at"])

    except Order.DoesNotExist:
        return error_response("NOT_FOUND", "Order not found.", 404)

    return JsonResponse(order_json(order))


@csrf_exempt
@require_http_methods(["POST"])
def confirm_order(request, order_number):
    return change_order_status(request, order_number, "confirm")


@csrf_exempt
@require_http_methods(["POST"])
def dispatch_order(request, order_number):
    return change_order_status(request, order_number, "dispatch")


@csrf_exempt
@require_http_methods(["POST"])
def deliver_order(request, order_number):
    return change_order_status(request, order_number, "deliver")


@csrf_exempt
@require_http_methods(["POST"])
def cancel_order(request, order_number):
    return change_order_status(request, order_number, "cancel")
@csrf_exempt
@require_http_methods(["POST"])

def supplier_sync(request):
    base_url = settings.SUPPLIER_API_URL.rstrip("/")
    api_key = settings.SUPPLIER_API_KEY
    print("DEBUG supplier URL:", repr(base_url))
    print("DEBUG supplier key configured:", bool(api_key))

    if not base_url or not api_key:
        print("CONFIG CHECK FAILED:", repr(base_url), bool(api_key))
        return error_response(
            "SUPPLIER_UNAVAILABLE",
            "Supplier URL or API key is not configured.",
            502,
        )

    session = requests.Session()
    session.headers.update({"X-Api-Key": api_key})

    items_by_sku = {}
    rejected = []
    pages_fetched = 0
    requests_made = 0
    cursor = None

    def parse_updated_at(value):
        try:
            if not value:
                return datetime.min.replace(tzinfo=dt_timezone.utc)
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_timezone.utc)
            return parsed
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=dt_timezone.utc)

    # Fetch every page before changing the database.
    try:
        while True:
            params = {"limit": 20}
            if cursor:
                params["cursor"] = cursor

            response = None

            for attempt in range(5):
                requests_made += 1

                try:
                    response = session.get(
                        f"{base_url}/v1/products",
                        params=params,
                        timeout=15,
                    )
                except requests.RequestException:
                    if attempt == 4:
                        raise
                    time.sleep(0.5 * (attempt + 1))
                    continue

                if response.status_code == 429:
                    if attempt == 4:
                        raise RuntimeError("Supplier rate limit retries exhausted")
                    try:
                        delay = max(0, float(response.headers.get("Retry-After", "1")))
                    except (ValueError, TypeError):
                        delay = 1
                    time.sleep(min(delay, 60))
                    continue

                if 500 <= response.status_code <= 599:
                    if attempt == 4:
                        raise RuntimeError("Supplier server retries exhausted")
                    time.sleep(0.5 * (attempt + 1))
                    continue

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Supplier returned HTTP {response.status_code}"
                    )

                break

            if response is None or response.status_code != 200:
                raise RuntimeError("Unable to fetch supplier page")

            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(
                payload.get("items"), list
            ):
                raise RuntimeError("Invalid supplier response")

            pages_fetched += 1

            for item in payload["items"]:
                if not isinstance(item, dict):
                    rejected.append({
                        "supplier_sku": None,
                        "reason": "invalid item",
                    })
                    continue

                sku = str(item.get("sku") or "").strip()
                if not sku:
                    rejected.append({
                        "supplier_sku": item.get("supplier_sku"),
                        "reason": "missing SKU",
                    })
                    continue

                try:
                    price = Decimal(str(item.get("price", "")))
                    if (
                        not price.is_finite()
                        or price <= 0
                        or price.as_tuple().exponent < -2
                    ):
                        raise ValueError
                except (InvalidOperation, ValueError, TypeError):
                    rejected.append({
                        "supplier_sku": item.get("supplier_sku"),
                        "reason": "invalid price",
                    })
                    continue

                normalized = dict(item)
                normalized["sku"] = sku
                normalized["price"] = price

                previous = items_by_sku.get(sku)
                if (
                    previous is None
                    or parse_updated_at(normalized.get("updated_at"))
                    >= parse_updated_at(previous.get("updated_at"))
                ):
                    items_by_sku[sku] = normalized

            cursor = payload.get("next_cursor")
            if cursor is None:
                break

    except (
    requests.RequestException,
    RuntimeError,
    ValueError,
    TypeError,
    ) as exc:
        print("SUPPLIER SYNC ERROR:", repr(exc))
        return error_response(
            "SUPPLIER_UNAVAILABLE",
            "Unable to complete supplier sync.",
            502,
        )
    except Exception:
        return error_response(
            "SUPPLIER_UNAVAILABLE",
            "Supplier returned an invalid response.",
            502,
        )
    finally:
        session.close()

    created = 0
    updated = 0
    unchanged = 0

    fields = (
        "name",
        "category",
        "brand",
        "vehicle_fitment",
        "description",
        "price",
    )

    try:
        with transaction.atomic():
            existing = {
                product.sku: product
                for product in Product.objects.select_for_update().filter(
                    sku__in=list(items_by_sku.keys())
                )
            }

            for sku, item in items_by_sku.items():
                values = {
                    "name": str(item.get("name") or "").strip(),
                    "category": str(item.get("category") or ""),
                    "brand": str(item.get("brand") or ""),
                    "vehicle_fitment": str(item.get("vehicle_fitment") or ""),
                    "description": str(item.get("description") or ""),
                    "price": item["price"],
                }

                product = existing.get(sku)

                if product is None:
                    Product.objects.create(
                        sku=sku,
                        **values,
                        stock=0,
                    )
                    created += 1
                    continue

                changed = any(
                    getattr(product, field) != value
                    for field, value in values.items()
                )

                if changed:
                    for field, value in values.items():
                        setattr(product, field, value)
                    product.save(update_fields=list(fields))
                    updated += 1
                else:
                    unchanged += 1

    except Exception:
        return error_response(
            "SUPPLIER_UNAVAILABLE",
            "Unable to apply supplier updates.",
            502,
        )

    return JsonResponse({
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "rejected": rejected,
        "pages_fetched": pages_fetched,
        "requests_made": requests_made,
    })
