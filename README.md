# TrustPay Backend

A Django REST API escrow service that sits between buyers and sellers, integrating with Payaza for payment processing. Holds deal state in SQLite — no Celery, no Redis, no async.

## Tech Stack

- **Django 6.0** + **Django REST Framework**
- **SQLite** (zero-config, default)
- **SimpleJWT** for authentication
- **Payaza API** for virtual accounts and payouts

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your SECRET_KEY and Payaza credentials

# 4. Run database migrations
python manage.py migrate

# 5. Start the development server
python manage.py runserver
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | `your-secret-key` |
| `DEBUG` | Debug mode toggle | `True` |
| `PAYAZA_BASE_URL` | Payaza API base URL | `https://api.payaza.africa` |
| `PAYAZA_PUBLIC_KEY` | Payaza public key | `PZ78-PKTEST-...` |
| `PAYAZA_TENANT_ID` | Payaza tenant ID | `test` |
| `PAYAZA_SECRET` | Payaza webhook secret | `your-webhook-secret-here` |

> Copy `.env.example` to `.env` and fill in your values. `.env` is already in `.gitignore`.

## API Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/login/` | Obtain JWT token pair | No |
| POST | `/api/auth/refresh/` | Refresh JWT access token | No |

### Deals (`/api/deals/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/deals/` | List all deals | Yes |
| POST | `/api/deals/` | Create a new deal | Yes |
| GET | `/api/deals/{slug}/` | Get deal details | Yes |
| POST | `/api/deals/{slug}/pay/` | Initiate payment (get VA) | Yes |
| POST | `/api/deals/{slug}/ship/` | Mark deal as shipped | Yes |
| POST | `/api/deals/{slug}/confirm/` | Confirm delivery | Yes |
| POST | `/api/deals/{slug}/dispute/` | Dispute a deal | Yes |

### Webhooks (`/api/webhooks/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/webhooks/payaza/` | Payaza payment callback | No (signature) |

### Admin

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/` | Django admin panel |

### Authentication Header

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

## Auto-Release Command

A management command checks for expired deals and auto-completes them:

```bash
python manage.py auto_release
```

This finds deals in `SHIPPED` status whose `auto_release_at` time has passed and transitions them to `COMPLETED`, triggering a payout to the seller.

## Testing with Payaza Sandbox

1. **Set up sandbox credentials** in your `.env` file:
   ```env
   PAYAZA_BASE_URL=https://api.payaza.africa
   PAYAZA_PUBLIC_KEY=PZ78-PKTEST-your-uuid-here
   PAYAZA_TENANT_ID=test
   PAYAZA_SECRET=your-webhook-secret-here
   ```

2. **Create a deal** and call the pay endpoint to get a virtual account number.

3. **Simulate a payment** by transferring to the VA from the Payaza sandbox dashboard, or use their test API to simulate a credit event.

4. **Verify the webhook** is received — check the deal status transitions to `PAID`:
   ```bash
   python manage.py runserver
   # In another terminal:
   curl http://localhost:8000/api/deals/<slug>/
   ```

5. **(Optional) Expose local server** for Payaza webhooks using a tool like ngrok:
   ```bash
   ngrok http 8000
   # Update your Payaza sandbox webhook URL to the ngrok URL + /api/webhooks/payaza/
   ```

## Project Structure

```
backend/              # Django project settings
users/                # User model and auth views
deals/                # Deal model, views, and auto-release command
payments/             # Payaza webhook handling
manage.py             # Django management script
```
