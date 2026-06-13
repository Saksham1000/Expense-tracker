import os
from decimal import Decimal
from datetime import date

import requests
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Category, Expense
from .serializers import CategorySerializer, ExpenseSerializer


def _get_rate_map(base, currencies):
    rates = {}
    for cur in currencies:
        if cur == base:
            rates[cur] = Decimal("1")
            continue
        try:
            r = requests.get(
                f"https://api.exchangerate.host/convert?from={cur}&to={base}&amount=1"
            )
            data = r.json()
            rate = Decimal(str(data.get("info", {}).get("rate") or data.get("result")))
        except Exception:
            rate = Decimal("1")
        rates[cur] = rate
    return rates


def _month_total_in_base(category, year, month, base, exclude_expense_id=None):
    qs = Expense.objects.filter(category=category, date__year=year, date__month=month)
    if exclude_expense_id:
        qs = qs.exclude(pk=exclude_expense_id)
    currencies = set(qs.values_list("currency", flat=True))
    rates = _get_rate_map(base, currencies)
    total = Decimal("0")
    for cur in currencies:
        s = qs.filter(currency=cur).aggregate(s=Sum("amount"))["s"] or 0
        s = Decimal(str(s))
        total += s * rates.get(cur, Decimal("1"))
    return total


def _send_budget_alert(category, total, limit, base):
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("BOT_CHAT_ID")
    if not token or not chat_id:
        return False
    text = (
        f"⚠️ Budget alert: \"{category.name}\" is over its monthly limit.\n"
        f"Spent {total:.2f} / {limit:.2f} {base} for {date.today().strftime('%B %Y')}."
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
        return resp.ok
    except Exception:
        return False


@api_view(["GET", "POST"])
def category_list(request):
    if request.method == "GET":
        categories = Category.objects.filter(owner=request.user)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    serializer = CategorySerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def expense_list(request):
    if request.method == "GET":
        expenses = Expense.objects.filter(owner=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)

        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    # Create: compute month-to-date totals before/after to possibly trigger alerts
    serializer = ExpenseSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)

    # determine category and month for threshold check
    cat_id = request.data.get("category")
    expense_date = request.data.get("date")
    if not cat_id:
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    try:
        category = Category.objects.get(pk=cat_id, owner=request.user)
    except Category.DoesNotExist:
        return Response({"category": ["Invalid category"]}, status=status.HTTP_400_BAD_REQUEST)

    # parse date
    if expense_date:
        y, m, _ = expense_date.split("-")
        year = int(y)
        month = int(m)
    else:
        today = date.today()
        year = today.year
        month = today.month

    base = os.getenv("BASE_CURRENCY", "USD")
    before_total = _month_total_in_base(category, year, month, base)

    expense = serializer.save()

    after_total = _month_total_in_base(category, year, month, base)
    limit = category.monthly_limit
    if limit is not None:
        limit_dec = Decimal(str(limit))
        if before_total <= limit_dec < after_total:
            _send_budget_alert(category, after_total, limit_dec, base)

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
def expense_detail(request, pk):
    try:
        expense = Expense.objects.get(pk=pk)
    except Expense.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if expense.owner != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)

    if request.method == "PUT":
        if expense.owner != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ExpenseSerializer(expense, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # prepare for threshold check
        cat_id = request.data.get("category") or expense.category_id
        expense_date = request.data.get("date") or str(expense.date)
        try:
            category = Category.objects.get(pk=cat_id, owner=request.user)
        except Category.DoesNotExist:
            return Response({"category": ["Invalid category"]}, status=status.HTTP_400_BAD_REQUEST)

        y, m, _ = expense_date.split("-")
        year = int(y)
        month = int(m)
        base = os.getenv("BASE_CURRENCY", "USD")
        before_total = _month_total_in_base(category, year, month, base, exclude_expense_id=expense.id)

        serializer.save()

        after_total = _month_total_in_base(category, year, month, base)
        limit = category.monthly_limit
        if limit is not None:
            limit_dec = Decimal(str(limit))
            if before_total <= limit_dec < after_total:
                _send_budget_alert(category, after_total, limit_dec, base)

        return Response(serializer.data)

    if expense.owner != request.user:
        return Response(status=status.HTTP_404_NOT_FOUND)
    expense.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
    


@api_view(["GET"])
def expense_summary(request):
    base = os.getenv("BASE_CURRENCY", "USD")
    # categories for user
    categories = Category.objects.filter(owner=request.user).order_by("name")

    # gather all currencies used in user's expenses
    expenses = Expense.objects.filter(owner=request.user)
    currencies = set(expenses.values_list("currency", flat=True))

    # fetch conversion rates to base currency (cache per currency)
    rates = {}
    for cur in currencies:
        if cur == base:
            rates[cur] = Decimal("1")
            continue
        try:
            r = requests.get(
                f"https://api.exchangerate.host/convert?from={cur}&to={base}&amount=1"
            )
            data = r.json()
            rate = Decimal(str(data.get("info", {}).get("rate") or data.get("result")))
        except Exception:
            rate = Decimal("1")
        rates[cur] = rate

    result = {"base_currency": base, "as_of": str(date.today()), "categories": []}
    for cat in categories:
        cat_expenses = expenses.filter(category=cat)
        total = Decimal("0")
        breakdown = []
        for cur in set(cat_expenses.values_list("currency", flat=True)):
            cur_sum = cat_expenses.filter(currency=cur).aggregate(s=Sum("amount"))["s"] or 0
            cur_sum = Decimal(str(cur_sum))
            converted = (cur_sum * rates.get(cur, Decimal("1")))
            breakdown.append({"currency": cur, "rate": str(rates.get(cur, "1")), "subtotal": str(round(converted, 2))})
            total += converted

        result["categories"].append({"category": cat.name, "total": str(round(total, 2)), "breakdown": breakdown})

    return Response(result)


@api_view(["GET"])
def export_expenses(request):
    import csv
    from django.http import HttpResponse

    expenses = Expense.objects.filter(owner=request.user).order_by("date")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = "attachment; filename=expenses.csv"
    writer = csv.writer(resp)
    writer.writerow(["id", "title", "amount", "currency", "category", "date", "notes"])
    for e in expenses:
        writer.writerow([e.id, e.title, str(e.amount), e.currency, e.category.name, e.date.isoformat(), e.notes])
    return resp


@api_view(["GET"])
def monthly_summary(request):
    # returns total spent for a given month (defaults to current month)
    year = int(request.query_params.get("year", date.today().year))
    month = int(request.query_params.get("month", date.today().month))
    qs = Expense.objects.filter(owner=request.user, date__year=year, date__month=month)
    total = qs.aggregate(s=Sum("amount"))["s"] or 0
    return Response({"year": year, "month": month, "total": str(total)})
