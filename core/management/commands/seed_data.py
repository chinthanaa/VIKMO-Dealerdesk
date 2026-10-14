
import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from core.models import Product, Dealer


class Command(BaseCommand):
    help = "Load catalogue and dealer CSV files safely and repeatedly."

    def handle(self, *args, **options):
        data_dir = Path(settings.DATA_DIR)

        catalogue_file = data_dir / "catalogue.csv"
        dealers_file = data_dir / "dealers.csv"

        if not catalogue_file.exists():
            raise CommandError(f"Missing file: {catalogue_file}")

        if not dealers_file.exists():
            raise CommandError(f"Missing file: {dealers_file}")

        products_created = 0
        products_updated = 0

        with catalogue_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                sku = row["sku"].strip()

                defaults = {
                    "name": row["name"].strip(),
                    "category": row.get("category", "").strip(),
                    "brand": row.get("brand", "").strip(),
                    "vehicle_fitment": row.get("vehicle_fitment", "").strip(),
                    "price": Decimal(row["price"]),
                    "description": row.get("description", "").strip(),
                }

                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults=defaults,
                )

                if created:
                    products_created += 1
                else:
                    products_updated += 1

        dealers_created = 0
        dealers_updated = 0

        with dealers_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                dealer_code = row["dealer_code"].strip()

                defaults = {
                    "name": row["name"].strip(),
                    "city": row.get("city", "").strip(),
                    "phone": row.get("phone", "").strip(),
                    "email": row.get("email", "").strip(),
                    "gstin": row.get("gstin", "").strip(),
                    "credit_limit": Decimal(
                        row.get("credit_limit", "0") or "0"
                    ),
                }

                dealer, created = Dealer.objects.update_or_create(
                    dealer_code=dealer_code,
                    defaults=defaults,
                )

                if created:
                    dealers_created += 1
                else:
                    dealers_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Products: {products_created} created, "
                f"{products_updated} updated. "
                f"Dealers: {dealers_created} created, "
                f"{dealers_updated} updated."
            )
        )
