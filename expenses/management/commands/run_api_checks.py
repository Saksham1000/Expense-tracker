from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Run internal API checks using the test client (no external server)."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com"},
        )
        if created:
            user.set_password("password")
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write("Created admin user with password 'password'")

        token, _ = Token.objects.get_or_create(user=user)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.stdout.write("1) Creating category 'Dining' with monthly_limit=200.00")
        r = client.post(
            "/api/categories/",
            {"name": "Dining", "monthly_limit": "200.00"},
            format="json",
        )
        self.stdout.write(f"status={r.status_code}, resp={r.data}")
        if r.status_code not in (200, 201):
            return
        cat_id = r.data.get("id")

        self.stdout.write("2) Creating expense in EUR (Hotel in Paris)")
        r = client.post(
            "/api/expenses/",
            {
                "title": "Hotel in Paris",
                "amount": "120.00",
                "currency": "EUR",
                "category": cat_id,
                "date": "2026-06-09",
            },
            format="json",
        )
        self.stdout.write(f"status={r.status_code}, resp={r.data}")

        self.stdout.write("3) Creating expense in USD (Dinner out)")
        r = client.post(
            "/api/expenses/",
            {
                "title": "Dinner out",
                "amount": "90.00",
                "currency": "USD",
                "category": cat_id,
                "date": "2026-06-10",
            },
            format="json",
        )
        self.stdout.write(f"status={r.status_code}, resp={r.data}")

        self.stdout.write("4) Creating another USD expense to potentially cross limit")
        r = client.post(
            "/api/expenses/",
            {
                "title": "Big dinner",
                "amount": "150.00",
                "currency": "USD",
                "category": cat_id,
                "date": "2026-06-11",
            },
            format="json",
        )
        self.stdout.write(f"status={r.status_code}, resp={r.data}")

        self.stdout.write("5) Fetching expense summary")
        r = client.get("/api/expenses/summary/")
        self.stdout.write(f"status={r.status_code}, resp={r.data}")
