# Expense Tracker 

A small Django REST Framework backend for tracking personal spending
(categories, expenses, date filtering, and a per-category summary).

## Your Task (read this first)

You will work with this codebase in four stages:

1. **Fix 5 bugs.** The code contains **5 intentional bugs**. Find and fix them
   all. Every hint you need is in the codebase or in this file.
2. **Add Authentication (required).** Scope expenses and categories to the
   logged-in user and protect the endpoints.
3. **Build 2 integration features (required):**
   [Currency conversion](#feature-1--currency-conversion) and
   [Budget threshold bot alerts](#feature-2--budget-threshold-bot-alerts).
   Both are specified in detail below, with example requests/responses — these
   are the hard part.
4. **Add 2 optional features** of your choice ([list below](#optional-pick-any-2)).

Config placeholders for stage 3 are already in `.env.example` — copy them into
your `.env`.

Full rules, branch naming, and submission details are in
[requirements](#full-requirements) at the bottom. Read that **before** writing
code — workflow is graded.

## What you've been given

| File / Dir                 | What it is                                              |
|----------------------------|---------------------------------------------------------|
| `expenses/`                | The app: `models.py`, `serializers.py`, `views.py`, `urls.py`, `tests.py` |
| `config/`                  | Django project settings and root URL config             |
| `postman_collection.json`  | **Ready-to-import Postman collection — every endpoint.** Use it to test and hunt bugs. |
| `.env.example`             | Template for your `.env`                                 |
| `pyproject.toml`           | Dependencies (managed by `uv`)                          |
| `manage.py`                | Django entry point                                      |

## Setup (3 commands)

Uses [uv](https://docs.astral.sh/uv/). Prefix every `manage.py` call with `uv run`.

```bash
uv sync                                  # create .venv + install deps
cp .env.example .env                     # then fill in SECRET_KEY
uv run python manage.py migrate          # set up the SQLite DB
uv run python manage.py runserver        # start at http://127.0.0.1:8000/
```

## Test the endpoints

1. Import `postman_collection.json` into Postman.
2. The `base_url` variable is preset to `http://127.0.0.1:8000`.
3. Run each request against your local server. **This is your main bug-hunting
   tool** — compare actual responses against the expected behavior below.

### Endpoints

| Method | Endpoint                 | Description                                                        |
|--------|--------------------------|-------------------------------------------------------------------|
| GET    | `/api/categories/`       | List all categories                                               |
| POST   | `/api/categories/`       | Create a category                                                 |
| GET    | `/api/expenses/`         | List expenses (filter with `?start_date=` & `?end_date=`, inclusive) |
| POST   | `/api/expenses/`         | Create an expense                                                 |
| GET    | `/api/expenses/{id}/`    | Retrieve one expense                                              |
| PUT    | `/api/expenses/{id}/`    | Update an expense                                                 |
| DELETE | `/api/expenses/{id}/`    | Delete an expense                                                 |
| GET    | `/api/expenses/summary/` | Total spent per category                                          |

## Tech stack

Python 3 · Django 5 · Django REST Framework · SQLite · python-dotenv

---

## Full Requirements

### Git workflow (graded)

- Create a new repo under **your** GitHub account.
- Default branch **must be named `trunk`** (not `main`/`master`).
- One branch + one PR per item:
  - Bug fixes → `fix/<bug-name>`
  - Features → `feature/<feature-name>`
- **Never commit fixes or features directly to `trunk`.** Merge via PR.
- Do **not** squash. Keep a clean, atomic, readable history. Push regularly.
- Each commit message must say **what** changed and **why**. Example:

  ```text
  fix(expenses): prevent negative expense amounts
  fix(api): correct serializer field mapping
  ```

### Required features

**Authentication** — expenses and categories owned by and scoped to the
authenticated user; endpoints protected (token/session auth + login).

Plus the two integration features below.

#### Feature 1 — Currency conversion

Let expenses be recorded in different currencies and reported in one base
currency, using a third-party exchange-rate API.

- Add a `currency` field to expenses (ISO code, e.g. `EUR`); `amount` stays in
  that currency.
- Reporting endpoints (e.g. `summary`) convert each amount to `BASE_CURRENCY`
  (see `.env.example`) using rates from an exchange-rate API.
- Free providers needing no key: `exchangerate.host`, `open.er-api.com`.

Example (illustrative — refine the exact shape as you see fit):

```jsonc
// POST /api/expenses/
{
  "title": "Hotel in Paris",
  "amount": "120.00",
  "currency": "EUR",
  "category": 1,
  "date": "2026-06-09"
}

// 201 Created
{
  "id": 7,
  "title": "Hotel in Paris",
  "amount": "120.00",
  "currency": "EUR",
  "category": 1,
  "date": "2026-06-09"
}
```

```jsonc
// GET /api/expenses/summary/   (BASE_CURRENCY = USD)
{
  "base_currency": "USD",
  "categories": [
    {
      "category": "Travel",
      "total": "129.60",        // 120.00 EUR converted at 1.08
      "rate": "1.08",
      "as_of": "2026-06-10"
    }
  ]
}
```

#### Feature 2 — Budget threshold bot alerts

Send a chat-bot alert when a category's spending crosses a configured limit.

- Add a per-category monthly budget limit.
- When a created/updated expense pushes that category's month-to-date total over
  its limit, send an alert via a bot (Telegram recommended — free token from
  `@BotFather`; Discord/Slack also fine). Credentials come from `.env`
  (`BOT_TOKEN`, `BOT_CHAT_ID`).

Example (illustrative — refine the exact shape as you see fit):

```jsonc
// Set a monthly limit on a category
// POST /api/categories/   (or PATCH an existing one)
{
  "name": "Dining",
  "monthly_limit": "200.00"
}
```

```jsonc
// POST /api/expenses/  — this expense pushes Dining's month total to 215.00,
// over its 200.00 limit, so an alert fires once.
{
  "title": "Dinner out",
  "amount": "45.00",
  "category": 3,
  "date": "2026-06-09"
}

// 201 Created — API responds normally; the alert is sent off the request path.
{
  "id": 12,
  "title": "Dinner out",
  "amount": "45.00",
  "category": 3,
  "date": "2026-06-09"
}
```

```text
Bot message delivered to BOT_CHAT_ID:

⚠️ Budget alert: "Dining" is over its monthly limit.
Spent 215.00 / 200.00 USD for June 2026.
```

Include **screenshots of the delivered bot alert** (the message in your
Telegram/Discord/Slack chat) in your README as proof it works.

#### Optional (pick any 2)

Recurring expenses · CSV export · Analytics dashboard · Expense
search/filtering · Monthly spending summaries · Favorite categories.

Each feature must be fully functional, follow existing API conventions, and
include validation. You may also improve the Django Admin.

### API documentation

- Update `postman_collection.json` with any new endpoints.
- Responses must carry enough data for a frontend to render views without extra
  follow-up requests.

### README write-up

In your README, add two sections:

- `## My Features` — for each feature (auth, currency conversion, bot alerts,
  and your optional one): overview, design decisions, API changes, example
  request/response, assumptions, known limits. For bot alerts, include
  **screenshots of the delivered alert**.
- `## Bugs Found and Fixed` — for each bug: description, root cause, fix, and
  commit hash.

### Submission

Submit: GitHub repo URL · updated Postman collection · updated README
(including bot-alert screenshots).

### Evaluation criteria

Commit quality · bug-fix correctness (no regressions) · feature design ·
Postman completeness · code readability · REST conventions (status codes,
response shape).

## My Features

- **Authentication:** Token and session auth enabled. Endpoints require an
  authenticated user; `Category` and `Expense` are scoped to their `owner`.
  - API: `POST /api/token-auth/` returns `{"token": "..."}`. Use header
   `Authorization: Token <token>`.

- **Currency conversion (required):** `Expense` has a `currency` field.
  The `GET /api/expenses/summary/` endpoint converts per-category totals to
  `BASE_CURRENCY` (set in `.env`) using `exchangerate.host` and returns a
  structured JSON with `base_currency`, `as_of`, and per-category `total` and
  `breakdown` entries.

- **Budget threshold bot alerts (required):** `Category` includes
  `monthly_limit`. Creating or updating an `Expense` will compute the
  month-to-date total (converted to `BASE_CURRENCY`) and, if the limit is
  crossed, send a Telegram alert using `BOT_TOKEN` and `BOT_CHAT_ID` from
  `.env`. If these are not set, alerts are skipped harmlessly.

- **Optional features:** CSV export (`GET /api/expenses/export/`) and
  monthly summary (`GET /api/expenses/monthly/?year=YYYY&month=M`).

## Bugs Found and Fixed

1. Serializer typo: `ExpenseSerializer` referenced `catgory` and returned
  wrong fields. Fixed fields to include `category`, `currency`, and `owner`.
2. Date filter logic: `start_date` used `date__gt` making it exclusive.
  Changed to `date__gte` for inclusive filtering.
3. Response typo: views returned `serialzer` in one place. Fixed to return
  `serializer`.
4. Missing imports/aggregation: `Sum` was referenced but not imported; fixed
  and implemented proper summary aggregation.
5. URL ordering: `expenses/<pk>/` matched `summary`; moved `summary` route
  before the detail route.

For each fix see commits in the repository history (branch names follow the
required convention). Add screenshots of bot alerts to this README after you
configure `BOT_TOKEN`/`BOT_CHAT_ID` and run an expense that crosses a limit.

## Running locally (quick)

1. Copy `.env.example` to `.env` and set `SECRET_KEY`. Optionally set
  `BASE_CURRENCY`, `BOT_TOKEN`, `BOT_CHAT_ID`.

2. Install and run:

```powershell
cd django-intern-project
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

3. Import `postman_collection.json` and use the `Obtain Token` request to
  authenticate. Use the token header for subsequent requests.

## Postman

`postman_collection.json` updated with new endpoints: `token-auth`,
`expenses/export`, and `expenses/monthly`.

