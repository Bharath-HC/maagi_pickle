# Maagi Pickle — E-Commerce Platform

**Maagi Pickle**, manufactured by **Prashanth Home Industries** (est. 2001), is a full-stack
corporate e-commerce web application for an authentic Indian pickle brand. It supports retail
customers as well as B2B Distributor and Wholesaler accounts, with a complete admin back office.

> **The True Taste of Tradition** — Authentic Indian Pickles Crafted with Tradition, Quality and Passion.

---

## 1. Overview

A production-style Flask application with:

- A single `User` table + role column (`ADMIN`, `DISTRIBUTOR`, `WHOLESALER`, `CUSTOMER`) driving
  role-based access control across four distinct dashboards — **not** four separate login systems.
- A full product catalog with pack-size variants (200g / 500g / 1kg / 2kg / 5kg), server-side
  role-based pricing, inventory tracking, coupons, reviews, wishlists and a persistent cart.
- A 4-step checkout with Razorpay-ready online payment (plus a documented dev-only simulation
  mode) and Cash on Delivery / Credit Terms.
- ReportLab-generated PDF invoices, a 10-stage order status pipeline with customer-facing
  tracking, and a notification system.
- Distributor/Wholesaler application + approval workflow, bulk order quote requests, and support
  tickets.
- A full admin console: product/category/inventory/order/coupon/review/banner management, sales
  analytics (5 Chart.js charts), CSV reporting, audit logs and settings.

## 2. Features Implemented

- **Authentication & Security** — registration, login (with role selection validated against the
  database, not just the form), logout, forgot/reset password architecture, password hashing
  (Werkzeug), login-attempt lockout, CSRF protection (Flask-WTF, including on every hand-written
  form), secure session cookies, role-based authorization decorators.
- **Catalog** — categories, products, pack-size variants, image galleries, featured products,
  stock tracking, SEO-friendly slugs.
- **Customer Portal** — dashboard, order history with a 7-step tracking timeline, wishlist,
  addresses, cart, coupons, invoice download, reorder, reviews (post-delivery, purchase-verified),
  notifications, profile.
- **Distributor & Wholesaler Portals** — dedicated dashboards, bulk ordering, orders, invoices,
  payments, their own downstream customer lists, and support tickets — all served from a single
  `b2b` blueprint parametrized by role, reusing one set of templates.
- **Admin Console** — full CRUD on products/variants/categories/coupons/banners, inventory with
  low-stock alerts and manual restock, order status management, B2B application approval
  (promotes the single `User` row's role), reviews moderation, bulk-quote handling, support ticket
  replies, contact enquiries, CSV sales export, audit log viewer, and a 5-chart sales dashboard.
- **Payments** — Razorpay order-create + Checkout.js + HMAC-SHA256 signature verification, with a
  clearly-labelled development-only simulation fallback when no Razorpay keys are configured.
- **Business rules** — server-side role pricing (customers can never obtain B2B pricing from the
  client), minimum order quantities for B2B accounts, GST calculation, coupon validation, stock
  reservation → deduction → restoration pipeline, 10 order statuses.
- **SEO & Accessibility** — meta/OpenGraph tags, canonical URLs, `robots.txt`, dynamic
  `sitemap.xml`, semantic HTML, alt text, keyboard-navigable menus.
- **Automated tests** — registration, per-role login/redirect, cross-role authorization checks,
  catalog/detail pages, role-based pricing, cart stock enforcement, COD checkout + inventory
  deduction, coupon minimum-order rejection.

## 3. Architecture

```
                         ┌────────────────────┐
                         │      User table      │
                         │  role: ADMIN /        │
                         │  DISTRIBUTOR /        │
                         │  WHOLESALER /         │
                         │  CUSTOMER             │
                         └──────────┬───────────┘
              ┌───────────┬─────────┼─────────┬───────────┐
              ▼           ▼         ▼         ▼            ▼
        Admin Console  Distributor  Wholesaler  Customer   (shared
        (/admin/*)     Portal       Portal      Portal     login/register)
                        (/distributor/*)(/wholesaler/*)(/customer/*)
              │           │         │         │
              └─────┬─────┴────┬────┴────┬────┘
                    ▼           ▼         ▼
            Shared Services: Products · Cart · Orders · Coupons ·
            Inventory · Notifications · Audit Log
                    │
                    ▼
            Payment Service → Razorpay (or dev simulation)
                    │
                    ▼
            Invoice Service (ReportLab PDF) → Inventory update
```

Flask **application factory** (`app/__init__.py`) + **Blueprints**: `main`, `auth`, `products`,
`cart`, `checkout`, `customer`, `b2b` (serves both Distributor and Wholesaler), `admin`, `api`.

## 4. Project Structure

```
maagi_pickle/
├── app/
│   ├── __init__.py            # application factory
│   ├── config.py               # Dev / Testing / Production config
│   ├── extensions.py           # db, migrate, login_manager, csrf
│   ├── forms.py                 # all WTForms
│   ├── models/                  # SQLAlchemy models (one file per domain)
│   ├── routes/                  # Blueprints (auth, main, products, cart, checkout,
│   │                             #   customer, b2b, admin, api)
│   ├── services/                 # business logic (pricing, cart, inventory, coupons,
│   │                             #   orders, payments, invoices, notifications, audit)
│   ├── utils/                    # decorators, helpers
│   ├── templates/                # Jinja2 templates (base, components, main, auth,
│   │                             #   products, customer, b2b, admin, errors)
│   └── static/
│       ├── css/main.css
│       ├── js/main.js
│       └── images/               # cropped brand assets (products, banners, branding,
│                                 #   categories, originals)
├── migrations/                   # Flask-Migrate (flask db init/migrate/upgrade)
├── tests/                        # pytest suite
├── instance/                      # local SQLite DB (gitignored)
├── seed.py                        # demo accounts + sample catalog
├── run.py                         # entrypoint
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Installation

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

## 6. Environment Configuration

Copy `.env.example` to `.env` and fill in the values you need:

```bash
cp .env.example .env
```

Key variables (see `.env.example` for the full list):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session/CSRF signing key — set a long random value in production |
| `DATABASE_URL` | Leave empty for local SQLite; set a `postgresql://...` URL in production |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Live/test Razorpay credentials |
| `ALLOW_PAYMENT_SIMULATION` | `true` in dev lets you test checkout without Razorpay keys; always `false` in production |
| `MAIL_*` | SMTP settings (wiring point for password-reset emails and notifications) |
| `COMPANY_*` | Shown on the site footer, invoices and contact page |

## 7. Database Setup & Seeding

```bash
# Option A — quick start (creates tables + demo data in one step)
python seed.py

# Option B — via Flask-Migrate (recommended once you start making schema changes)
flask db init        # first time only
flask db migrate -m "Initial schema"
flask db upgrade
flask seed            # runs the same seeding logic as seed.py
```

`seed.py` creates:
- 4 demo accounts (Admin, Distributor, Wholesaler, Customer)
- 3 categories and 4 products (Dry Fruit, Lemon Chilli, Mango, Mixed Veg Pickle) each with real
  pack-size variants (200g/500g/1kg/[2kg]/5kg)
- A demo coupon (`MAAGI10`) and a homepage banner
- All demo prices are clearly marked (`is_demo=True`) and are **not** official Maagi Pickle prices

## 8. Running the App

```bash
python run.py
```

The app starts at **http://127.0.0.1:5000**.

### Demo Credentials (development only)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@maagi.local` | `Maagi@12345` |
| Distributor | `distributor@maagi.local` | `Maagi@12345` |
| Wholesaler | `wholesaler@maagi.local` | `Maagi@12345` |
| Customer | `customer@maagi.local` | `Maagi@12345` |

> ⚠️ These are **development-only** seed accounts with a shared demo password
> (`DEMO_PASSWORD` in `.env`). Never use these credentials, or ship this seed data, in production.

### Main URLs

| Area | URL |
|---|---|
| Storefront | `/` |
| Product catalog | `/products/` |
| Bulk orders | `/bulk-orders` |
| Become a Distributor/Wholesaler | `/become-a-distributor`, `/become-a-wholesaler` |
| Login / Register | `/login`, `/register` |
| Customer dashboard | `/customer/dashboard` |
| Distributor dashboard | `/distributor/dashboard` |
| Wholesaler dashboard | `/wholesaler/dashboard` |
| Admin console | `/admin/dashboard` |
| REST API | `/api/products`, `/api/orders`, `/api/admin/*` |

## 9. Testing

```bash
pytest -q
```

The suite (17 tests) covers registration, per-role login/dashboard routing, cross-role
authorization boundaries (a Customer or Wholesaler cannot reach another role's dashboard, even by
direct URL), catalog/detail pages, server-side role-based pricing, cart stock/MOQ enforcement, a
full COD checkout with inventory deduction, and coupon minimum-order validation.

## 10. Razorpay Setup

1. Create a Razorpay account and generate API keys (Test mode is fine for staging).
2. Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`.
3. With keys configured, `/checkout/pay/<order>` automatically switches from the dev simulation
   button to the real Razorpay Checkout.js flow, and `ALLOW_PAYMENT_SIMULATION` is ignored.
4. Signature verification uses HMAC-SHA256 over `razorpay_order_id|razorpay_payment_id` with your
   key secret (`app/services/payment_service.py`), and is idempotent against duplicate callbacks.
5. The `/checkout/pay/<order>/verify` endpoint is intentionally CSRF-exempt, because Razorpay's
   client-side Checkout.js posts the callback without a Flask-issued CSRF token — this is
   documented in `app/routes/checkout.py`.

## 11. Production Deployment

```bash
# 1. Environment
export FLASK_ENV=production
export SECRET_KEY="<32+ character random string>"
export DATABASE_URL="postgresql://user:password@host:5432/maagi"
export RAZORPAY_KEY_ID="rzp_live_..."
export RAZORPAY_KEY_SECRET="..."
export ALLOW_PAYMENT_SIMULATION=false

# 2. Migrate the schema
flask db upgrade

# 3. Run with Gunicorn behind Nginx
gunicorn -w 4 -b 127.0.0.1:8000 run:app
```

Example Nginx reverse-proxy snippet:

```nginx
server {
    listen 80;
    server_name www.maagipickle.example;

    location /static/ {
        alias /path/to/maagi_pickle/app/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Put TLS termination (Let's Encrypt/Certbot) in front of Nginx and redirect HTTP → HTTPS.
`ProductionConfig` enforces secure cookies and will refuse to start with a default/weak
`SECRET_KEY`.

## 12. Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never stored or logged in
  plaintext.
- CSRF protection (Flask-WTF `CSRFProtect`) is enabled application-wide; every hand-written form
  carries a `csrf_token` hidden field. The one documented exception is the Razorpay payment
  callback endpoint, which cannot carry a Flask-issued token.
- Role is read from the database on every request via `current_user.role`; it can never be
  changed by a client-submitted field. Role-based prices are resolved entirely server-side
  (`app/services/pricing_service.py`) — the client never receives another role's pricing.
- File uploads are restricted to `jpg/jpeg/png/webp`, renamed to random filenames, and size-capped
  via `MAX_CONTENT_LENGTH`.
- All database access goes through the SQLAlchemy ORM (no raw/string-interpolated SQL).
- `.env` is gitignored; only `.env.example` (with no real secrets) is committed.
- An `AuditLog` records admin and sensitive user actions (logins, CRUD, price/stock changes, order
  status changes, B2B approvals, coupon creation) with user, IP and timestamp.

---

© Prashanth Home Industries. Maagi Pickle — *The True Taste of Tradition.*
