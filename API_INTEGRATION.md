# TrustPay API Integration Guide

**Version:** 1.0.0  
**Last Updated:** May 2026

A complete reference for frontend developers integrating with the TrustPay escrow payment API.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Merchant Dashboard](#3-merchant-dashboard)
4. [Payment Links](#4-payment-links)
5. [Deal Lifecycle](#5-deal-lifecycle)
6. [Webhooks](#6-webhooks)
7. [Error Handling](#7-error-handling)
8. [Rate Limits](#8-rate-limits)

---

## 1. Overview

### What is TrustPay?

TrustPay is an escrow payment platform that sits between buyers and sellers to enable secure transactions. The platform:

- Holds buyer payments in escrow until goods/services are delivered
- Provides virtual account numbers for receiving payments via Payaza
- Manages the complete deal lifecycle from creation to completion
- Handles disputes with admin intervention when needed
- Automatically releases funds to sellers after delivery confirmation or grace period expiry

### Base URLs

| Environment | Base URL |
|-------------|----------|
| Production | `https://api.trustpay.ng` |
| Development | `http://localhost:8000` |

All API paths in this document are relative to the base URL. For example, `/api/auth/login/` becomes:
- Production: `https://api.trustpay.ng/api/auth/login/`
- Development: `http://localhost:8000/api/auth/login/`

### Authentication Method

TrustPay uses **JWT (JSON Web Tokens)** with access and refresh tokens:

- **Access Token:** Short-lived (default 5 minutes). Sent with every authenticated request.
- **Refresh Token:** Long-lived (default 7 days). Used to obtain new access tokens.

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Common Headers

```http
Content-Type: application/json
Authorization: Bearer <access_token>  (for authenticated endpoints)
```

---

## 2. Authentication

### 2.1 Register New User

Creates a new user account.

**Endpoint:** `POST /api/auth/register/`  
**Auth Required:** No

**Request Body:**

```json
{
  "username": "seller1",
  "password": "securepass123",
  "email": "seller@example.com",
  "phone": "08012345678",
  "bank_name": "GTBank",
  "bank_account_number": "0123456789",
  "bank_code": "058",
  "is_merchant": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username |
| `password` | string | Yes | Minimum 6 characters |
| `email` | string | No | User email address |
| `phone` | string | No | Phone number |
| `bank_name` | string | No | Bank name for payouts |
| `bank_account_number` | string | No | Account number for payouts |
| `bank_code` | string | No | Bank code (e.g., "058" for GTBank) |
| `is_merchant` | boolean | No | Set to `true` for seller accounts |

**Response (201 Created):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "username": "seller1",
  "email": "seller@example.com",
  "phone": "08012345678",
  "bank_name": "GTBank",
  "bank_account_number": "0123456789",
  "bank_code": "058",
  "is_merchant": true
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 201 | User created successfully |
| 400 | Validation error (e.g., username taken, weak password) |

---

### 2.2 Login

Obtains JWT access and refresh tokens.

**Endpoint:** `POST /api/auth/login/`  
**Auth Required:** No

**Request Body:**

```json
{
  "username": "seller1",
  "password": "securepass123"
}
```

**Response (200 OK):**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE1MTIzNDU2LCJpYXQiOjE3MTUxMjMxNTYsImp0aSI6ImFiYzEyMyIsInVzZXJfaWQiOjF9.abc123",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTcxNTcyNzk1NiwiaWF0IjoxNzE1MTIzMTU2LCJqdGkiOiJkZWY0NTYiLCJ1c2VyX2lkIjoxfQ.def456"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access` | string | Access token (short-lived, ~5 minutes) |
| `refresh` | string | Refresh token (long-lived, ~7 days) |

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Login successful |
| 401 | Invalid credentials |

---

### 2.3 Refresh Token

Obtains a new access token using a refresh token.

**Endpoint:** `POST /api/auth/refresh/`  
**Auth Required:** No

**Request Body:**

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTcxNTcyNzk1NiwiaWF0IjoxNzE1MTIzMTU2LCJqdGkiOiJkZWY0NTYiLCJ1c2VyX2lkIjoxfQ.def456"
}
```

**Response (200 OK):**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE1MTIzNzU2LCJpYXQiOjE3MTUxMjM0NTYsImp0aSI6ImdoaTc4OSIsInVzZXJfaWQiOjF9.ghi789"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Token refreshed successfully |
| 401 | Invalid or expired refresh token |

---

## 3. Merchant Dashboard

### 3.1 Dashboard Stats

Retrieves merchant statistics and recent deals.

**Endpoint:** `GET /api/merchant/dashboard/`  
**Auth Required:** Yes

**Response (200 OK):**

```json
{
  "total_deals": 47,
  "active_deals": 12,
  "completed_deals": 32,
  "disputed_deals": 3,
  "total_revenue": "1250000.00",
  "pending_revenue": "340000.00",
  "recent_deals": [
    {
      "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "slug": "iphone-15-pro-abc123",
      "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "buyer_email": "buyer@example.com",
      "buyer_phone": "08098765432",
      "item_description": "iPhone 15 Pro",
      "amount": "850000.00",
      "delivery_days": 3,
      "status": "PAID",
      "va_account_number": "1234567890",
      "va_bank_name": "GTBank",
      "va_reference": "VA-REF-123456",
      "created_at": "2026-05-01T10:30:00Z",
      "paid_at": "2026-05-01T14:20:00Z",
      "shipped_at": null,
      "auto_release_at": null,
      "completed_at": null,
      "trust_fee_percent": "1.50"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_deals` | integer | Total number of deals |
| `active_deals` | integer | Deals in PENDING_PAYMENT, PAID, or SHIPPED status |
| `completed_deals` | integer | Deals in COMPLETED status |
| `disputed_deals` | integer | Deals in DISPUTED status |
| `total_revenue` | decimal | Sum of amounts from completed deals |
| `pending_revenue` | decimal | Sum of amounts from PAID and SHIPPED deals |
| `recent_deals` | array | Last 5 deals sorted by creation date |

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |

---

### 3.2 List Merchant Deals

Retrieves all deals for the authenticated merchant.

**Endpoint:** `GET /api/merchant/deals/?status=PAID`  
**Auth Required:** Yes

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by deal status (e.g., PAID, SHIPPED, COMPLETED) |

**Response (200 OK):**

```json
[
  {
    "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "slug": "iphone-15-pro-abc123",
    "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "buyer_email": "buyer@example.com",
    "buyer_phone": "08098765432",
    "item_description": "iPhone 15 Pro",
    "amount": "850000.00",
    "delivery_days": 3,
    "status": "PAID",
    "va_account_number": "1234567890",
    "va_bank_name": "GTBank",
    "va_reference": "VA-REF-123456",
    "created_at": "2026-05-01T10:30:00Z",
    "paid_at": "2026-05-01T14:20:00Z",
    "shipped_at": null,
    "auto_release_at": null,
    "completed_at": null,
    "trust_fee_percent": "1.50"
  }
]
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |

---

### 3.3 Get Deal Details (Merchant View)

Retrieves details for a specific deal owned by the merchant.

**Endpoint:** `GET /api/merchant/deals/{slug}/`  
**Auth Required:** Yes

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier (e.g., `iphone-15-pro-abc123`) |

**Response (200 OK):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "status": "PAID",
  "va_account_number": "1234567890",
  "va_bank_name": "GTBank",
  "va_reference": "VA-REF-123456",
  "created_at": "2026-05-01T10:30:00Z",
  "paid_at": "2026-05-01T14:20:00Z",
  "shipped_at": null,
  "auto_release_at": null,
  "completed_at": null,
  "trust_fee_percent": "1.50"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |
| 403 | Deal does not belong to authenticated user |
| 404 | Deal not found |

---

### 3.4 List Merchant Transactions

Retrieves transaction history for the merchant.

**Endpoint:** `GET /api/merchant/transactions/`  
**Auth Required:** Yes

**Response (200 OK):**

```json
[
  {
    "id": "tx-123456",
    "deal": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "tx_type": "COLLECTION",
    "status": "SUCCESS",
    "amount": "850000.00",
    "payaza_ref": "PAY-REF-789012",
    "created_at": "2026-05-01T14:20:00Z"
  },
  {
    "id": "tx-789012",
    "deal": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "tx_type": "PAYOUT",
    "status": "SUCCESS",
    "amount": "850000.00",
    "payaza_ref": "PO-REF-345678",
    "created_at": "2026-05-05T09:15:00Z"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | uuid | Transaction ID |
| `deal` | uuid | Associated deal ID |
| `tx_type` | string | `COLLECTION`, `PAYOUT`, or `REFUND` |
| `status` | string | `PENDING`, `SUCCESS`, or `FAILED` |
| `amount` | decimal | Transaction amount |
| `payaza_ref` | string | Payaza transaction reference |
| `created_at` | datetime | Transaction timestamp |

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |

---

## 4. Payment Links

### 4.1 List Payment Links

Retrieves all payment links created by the merchant.

**Endpoint:** `GET /api/merchant/links/`  
**Auth Required:** Yes

**Response (200 OK):**

```json
[
  {
    "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "slug": "iphone-15-pro-abc123",
    "link_url": "https://trustpay.ng/pay/iphone-15-pro-abc123",
    "item_description": "iPhone 15 Pro",
    "amount": "850000.00",
    "status": "PENDING_PAYMENT",
    "created_at": "2026-05-01T10:30:00Z",
    "delivery_days": 3
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | uuid | Deal ID |
| `slug` | string | Unique slug for the payment link |
| `link_url` | string | Full URL for the payment page |
| `item_description` | string | Item description |
| `amount` | decimal | Payment amount |
| `status` | string | Current deal status |
| `created_at` | datetime | Creation timestamp |
| `delivery_days` | integer | Expected delivery days |

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |

---

### 4.2 Create Payment Link

Creates a new payment link (deal) for receiving payments.

**Endpoint:** `POST /api/merchant/links/`  
**Auth Required:** Yes

**Request Body:**

```json
{
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_description` | string | Yes | Description of item/service |
| `amount` | decimal | Yes | Payment amount |
| `delivery_days` | integer | No | Expected delivery days (default: 3) |
| `buyer_email` | string | No | Buyer email (optional) |
| `buyer_phone` | string | No | Buyer phone (optional) |

**Response (201 Created):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "link_url": "https://trustpay.ng/pay/iphone-15-pro-abc123",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "status": "PENDING_PAYMENT",
  "created_at": "2026-05-01T10:30:00Z",
  "delivery_days": 3
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 201 | Payment link created |
| 400 | Validation error |
| 401 | Unauthorized |

---

## 5. Deal Lifecycle

### 5.1 List All Deals

Retrieves deals where the user is either buyer or seller.

**Endpoint:** `GET /api/deals/`  
**Auth Required:** Yes

**Response (200 OK):**

```json
[
  {
    "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "slug": "iphone-15-pro-abc123",
    "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "buyer_email": "buyer@example.com",
    "buyer_phone": "08098765432",
    "item_description": "iPhone 15 Pro",
    "amount": "850000.00",
    "delivery_days": 3,
    "status": "PAID",
    "va_account_number": "1234567890",
    "va_bank_name": "GTBank",
    "va_reference": "VA-REF-123456",
    "created_at": "2026-05-01T10:30:00Z",
    "paid_at": "2026-05-01T14:20:00Z",
    "shipped_at": null,
    "auto_release_at": null,
    "completed_at": null,
    "trust_fee_percent": "1.50"
  }
]
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |

---

### 5.2 Create Deal

Creates a new deal.

**Endpoint:** `POST /api/deals/`  
**Auth Required:** Yes

**Request Body:**

```json
{
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432"
}
```

**Response (201 Created):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "status": "PENDING_PAYMENT",
  "va_account_number": "",
  "va_bank_name": "",
  "va_reference": "",
  "created_at": "2026-05-01T10:30:00Z",
  "paid_at": null,
  "shipped_at": null,
  "auto_release_at": null,
  "completed_at": null,
  "trust_fee_percent": "1.50"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 201 | Deal created |
| 400 | Validation error |
| 401 | Unauthorized |

---

### 5.3 Get Deal Details

Retrieves details for a specific deal.

**Endpoint:** `GET /api/deals/{slug}/`  
**Auth Required:** No (if status is PENDING_PAYMENT), Yes (otherwise)

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier |

**Response (200 OK):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "status": "PAID",
  "va_account_number": "1234567890",
  "va_bank_name": "GTBank",
  "va_reference": "VA-REF-123456",
  "created_at": "2026-05-01T10:30:00Z",
  "paid_at": "2026-05-01T14:20:00Z",
  "shipped_at": null,
  "auto_release_at": null,
  "completed_at": null,
  "trust_fee_percent": "1.50"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized (for non-PENDING_PAYMENT deals) |
| 404 | Deal not found |

---

### 5.4 Initiate Payment (Get Virtual Account)

Generates a virtual account number for receiving payment.

**Endpoint:** `POST /api/deals/{slug}/pay/`  
**Auth Required:** No

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier |

**Request Body:** None

**Response (200 OK):**

```json
{
  "va_account_number": "1234567890",
  "va_bank_name": "GTBank",
  "amount": "850000.00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `va_account_number` | string | Virtual account number to transfer to |
| `va_bank_name` | string | Bank name for the virtual account |
| `amount` | decimal | Exact amount to transfer |

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Virtual account generated |
| 400 | Deal is not in PENDING_PAYMENT status |
| 404 | Deal not found |

---

### 5.5 Mark as Shipped

Seller marks the deal as shipped after receiving payment.

**Endpoint:** `POST /api/deals/{slug}/ship/`  
**Auth Required:** Yes (seller only)

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier |

**Request Body:** None

**Response (200 OK):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "status": "SHIPPED",
  "va_account_number": "1234567890",
  "va_bank_name": "GTBank",
  "va_reference": "VA-REF-123456",
  "created_at": "2026-05-01T10:30:00Z",
  "paid_at": "2026-05-01T14:20:00Z",
  "shipped_at": "2026-05-02T09:00:00Z",
  "auto_release_at": "2026-05-06T09:00:00Z",
  "completed_at": null,
  "trust_fee_percent": "1.50"
}
```

**Important:** This endpoint sets `auto_release_at` to `shipped_at + delivery_days + 1 day`. After this time, the deal will auto-complete if not disputed.

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Deal marked as shipped |
| 400 | Deal is not in PAID status |
| 401 | Unauthorized |
| 403 | Only the seller can mark as shipped |
| 404 | Deal not found |

---

### 5.6 Confirm Delivery

Buyer confirms receipt of goods/services, triggering payout to seller.

**Endpoint:** `POST /api/deals/{slug}/confirm/`  
**Auth Required:** No

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier |

**Request Body:** None

**Response (200 OK):**

```json
{
  "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "slug": "iphone-15-pro-abc123",
  "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "buyer_email": "buyer@example.com",
  "buyer_phone": "08098765432",
  "item_description": "iPhone 15 Pro",
  "amount": "850000.00",
  "delivery_days": 3,
  "status": "COMPLETED",
  "va_account_number": "1234567890",
  "va_bank_name": "GTBank",
  "va_reference": "VA-REF-123456",
  "created_at": "2026-05-01T10:30:00Z",
  "paid_at": "2026-05-01T14:20:00Z",
  "shipped_at": "2026-05-02T09:00:00Z",
  "auto_release_at": "2026-05-06T09:00:00Z",
  "completed_at": "2026-05-04T15:30:00Z",
  "trust_fee_percent": "1.50"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Deal completed, payout initiated |
| 400 | Deal is not in SHIPPED status or has open dispute |
| 404 | Deal not found |
| 502 | Payout to seller failed (retry possible) |

---

### 5.7 Dispute Deal

Buyer or seller opens a dispute, pausing the deal.

**Endpoint:** `POST /api/deals/{slug}/dispute/`  
**Auth Required:** No

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Unique deal identifier |

**Request Body:**

```json
{
  "reason": "Item not received as described. Screen has scratches."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Detailed reason for the dispute |

**Response (200 OK):**

```json
{
  "dispute_id": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
  "status": "OPEN"
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Dispute opened |
| 400 | Cannot dispute this deal (invalid status) or deal already has a dispute |
| 404 | Deal not found |

---

### 5.8 List Disputes (Admin Only)

Retrieves all open disputes for admin review.

**Endpoint:** `GET /api/admin/disputes/`  
**Auth Required:** Yes (admin/staff only)

**Response (200 OK):**

```json
[
  {
    "id": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
    "deal": {
      "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "slug": "iphone-15-pro-abc123",
      "seller": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "buyer_email": "buyer@example.com",
      "item_description": "iPhone 15 Pro",
      "amount": "850000.00",
      "status": "DISPUTED"
    },
    "reason": "Item not received as described. Screen has scratches.",
    "status": "OPEN",
    "created_at": "2026-05-03T10:00:00Z",
    "resolved_at": null
  }
]
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |
| 403 | Not an admin user |

---

### 5.9 Resolve Dispute (Admin Only)

Admin resolves a dispute by refunding buyer or releasing to seller.

**Endpoint:** `POST /api/admin/disputes/{id}/resolve/`  
**Auth Required:** Yes (admin/staff only)

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Dispute ID |

**Request Body:**

```json
{
  "action": "refund"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | Either `"refund"` (return to buyer) or `"release"` (pay seller) |

**Response (200 OK) - Refund:**

```json
{
  "dispute": {
    "id": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
    "deal": {
      "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "slug": "iphone-15-pro-abc123",
      "status": "REFUNDED"
    },
    "reason": "Item not received as described.",
    "status": "RESOLVED_REFUND",
    "created_at": "2026-05-03T10:00:00Z",
    "resolved_at": "2026-05-04T11:00:00Z"
  },
  "deal": {
    "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "slug": "iphone-15-pro-abc123",
    "status": "REFUNDED",
    "amount": "850000.00"
  }
}
```

**Response (200 OK) - Release:**

```json
{
  "dispute": {
    "id": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
    "deal": {
      "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "slug": "iphone-15-pro-abc123",
      "status": "COMPLETED"
    },
    "reason": "Item not received as described.",
    "status": "RESOLVED_RELEASE",
    "created_at": "2026-05-03T10:00:00Z",
    "resolved_at": "2026-05-04T11:00:00Z"
  },
  "deal": {
    "id": "a3f8b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "slug": "iphone-15-pro-abc123",
    "status": "COMPLETED",
    "amount": "850000.00",
    "completed_at": "2026-05-04T11:00:00Z"
  }
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Dispute resolved |
| 400 | Dispute already resolved or invalid action |
| 401 | Unauthorized |
| 403 | Not an admin user |
| 404 | Dispute not found |

---

## 6. Webhooks

### Payaza Webhook Handler

TrustPay receives payment events from Payaza via webhooks. This is for backend reference only.

**Endpoint:** `POST /api/webhooks/payaza/`  
**Auth Required:** No (uses signature verification)

**Headers:**

```http
X-PAYAZA-SIGN: <signature>
Content-Type: application/json
```

**Request Body (Payment Success):**

```json
{
  "event_type": "payment.success",
  "reference": "VA-REF-123456",
  "transaction_id": "PAY-REF-789012",
  "amount": "850000.00",
  "status": "completed"
}
```

**Request Body (Payout Success):**

```json
{
  "event_type": "payout.success",
  "reference": "PO-REF-345678",
  "transaction_id": "PO-TXN-901234",
  "amount": "850000.00",
  "status": "completed"
}
```

**Response (200 OK):**

```json
{
  "status": "received"
}
```

**Event Types:**

| Event Type | Description |
|------------|-------------|
| `payment.success` | Buyer payment received |
| `payment.failed` | Buyer payment failed |
| `payout.success` | Seller payout completed |
| `payout.failed` | Seller payout failed |

---

## 7. Error Handling

### Standard Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": "Human-readable error message"
}
```

**Validation Errors (400 Bad Request):**

```json
{
  "username": ["A user with that username already exists."],
  "password": ["Ensure this field has at least 6 characters."]
}
```

**Authentication Errors (401 Unauthorized):**

```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is expired"
    }
  ]
}
```

**Common Status Codes:**

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Proceed with response data |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Fix validation errors in request |
| 401 | Unauthorized | Refresh token or re-authenticate |
| 403 | Forbidden | User lacks permission for this action |
| 404 | Not Found | Resource does not exist |
| 502 | Bad Gateway | External service (Payaza) error, retry later |

---

## 8. Rate Limits

**Note:** The MVP version of TrustPay does not implement rate limiting. All endpoints are available without request throttling.

For production deployments, consider implementing rate limits based on your infrastructure capacity.

---

## Appendix A: Deal Status Flow

```
PENDING_PAYMENT
      │
      ▼ (payment received via webhook)
     PAID
      │
      ▼ (seller ships)
    SHIPPED
      │
      ├─────────────┐
      ▼             ▼
  (confirm)     (dispute)
      │             │
      ▼             ▼
  COMPLETED     DISPUTED
                  │
                  ▼ (admin resolves)
         ┌────────┴────────┐
         ▼                 ▼
   REFUNDED           COMPLETED
```

### Status Descriptions

| Status | Description |
|--------|-------------|
| `PENDING_PAYMENT` | Deal created, waiting for buyer payment |
| `PAID` | Payment received, seller should ship |
| `SHIPPED` | Seller has shipped, awaiting buyer confirmation |
| `DELIVERED` | Buyer confirmed delivery (transient, quickly becomes COMPLETED) |
| `COMPLETED` | Deal finished, seller paid |
| `DISPUTED` | Dispute opened, admin review required |
| `REFUNDED` | Deal refunded to buyer |

### Auto-Release

When a deal is marked as `SHIPPED`, the system calculates:

```
auto_release_at = shipped_at + delivery_days + 1 day (grace period)
```

A background command (`python manage.py auto_release`) checks for deals past their `auto_release_at` time and automatically transitions them to `COMPLETED`, triggering payout to the seller.

---

## Appendix B: Quick Start Example

```javascript
// 1. Register
const register = await fetch('http://localhost:8000/api/auth/register/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'seller1',
    password: 'securepass123',
    email: 'seller@example.com',
    is_merchant: true
  })
});

// 2. Login
const login = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'seller1',
    password: 'securepass123'
  })
});
const { access, refresh } = await login.json();

// 3. Create a deal
const deal = await fetch('http://localhost:8000/api/deals/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access}`
  },
  body: JSON.stringify({
    item_description: 'iPhone 15 Pro',
    amount: '850000.00',
    delivery_days: 3,
    buyer_email: 'buyer@example.com'
  })
});
const { slug } = await deal.json();

// 4. Get virtual account for payment
const pay = await fetch(`http://localhost:8000/api/deals/${slug}/pay/`, {
  method: 'POST'
});
const { va_account_number, va_bank_name, amount } = await pay.json();

// Share va_account_number and va_bank_name with buyer for transfer
```

---

## Appendix C: Support

For API issues or questions:
- GitHub: [TrustPay Backend Repository](https://github.com/your-org/trust-pay-backend)
- Email: support@trustpay.ng
