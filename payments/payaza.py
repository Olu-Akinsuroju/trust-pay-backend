import base64
import hashlib
import hmac
import random
import requests
from django.conf import settings


class PayazaError(Exception):
    def __init__(self, message, status_code=None, response_data=None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


def _mock_mode():
    return getattr(settings, 'PAYAZA_MOCK_MODE', False)


def _payaza_headers():
    key = base64.b64encode(settings.PAYAZA_PUBLIC_KEY.encode()).decode()
    return {
        'Authorization': f'Payaza {key}',
        'X-TenantID': settings.PAYAZA_TENANT_ID,
        'Content-Type': 'application/json',
    }


def _url(path):
    tenant = settings.PAYAZA_TENANT_ID
    return f"{settings.PAYAZA_BASE_URL}/{tenant}{path}"


def create_virtual_account(deal):
    if _mock_mode():
        return {
            "account_number": f"{random.randint(1000000000, 9999999999)}",
            "bank_name": "Payaza Test Bank",
            "reference": str(deal.id),
        }
    try:
        resp = requests.post(
            _url("/payaza-account/api/v1/mainaccounts/merchant/virtual-account"),
            json={
                "amount": str(deal.amount),
                "reference": str(deal.id),
                "customer_email": deal.buyer_email or "",
                "customer_phone": deal.buyer_phone or "",
            },
            headers=_payaza_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PayazaError(
            "Failed to create virtual account",
            status_code=getattr(e.response, 'status_code', None),
            response_data=e.response.text if e.response else None,
        ) from e
    data = resp.json()
    return {
        "account_number": data.get("account_number", ""),
        "bank_name": data.get("bank_name", ""),
        "reference": data.get("reference", str(deal.id)),
    }


def payout_seller(deal):
    if _mock_mode():
        return {
            "status": "success",
            "transaction_id": f"mock-payout-{deal.id}",
            "message": "Mock payout successful",
        }
    net = deal.amount - (deal.amount * deal.trust_fee_percent / 100)
    payload = {
        "account_number": deal.seller.bank_account_number,
        "bank_code": deal.seller.bank_code,
        "amount": str(net),
        "currency": "NGN",
        "narration": f"TrustPay {deal.item_description}",
        "reference": f"payout-{deal.id}",
    }
    beneficiary_name = getattr(deal.seller, 'bank_account_name', '') or deal.seller.get_full_name() or deal.seller.username
    if beneficiary_name:
        payload["beneficiary_name"] = beneficiary_name
    pin = getattr(settings, 'PAYAZA_TRANSACTION_PIN', None)
    if pin:
        payload["pin"] = str(pin)
    try:
        resp = requests.post(
            _url("/payout-receptor/payout"),
            json=payload,
            headers=_payaza_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PayazaError(
            "Failed to process payout",
            status_code=getattr(e.response, 'status_code', None),
            response_data=e.response.text if e.response else None,
        ) from e
    return resp.json()


def refund_buyer(deal):
    if _mock_mode():
        return {
            "status": "success",
            "transaction_id": f"mock-refund-{deal.id}",
            "message": "Mock refund successful",
        }
    payload = {
        "account_number": deal.buyer_phone or "",
        "bank_code": "",
        "amount": str(deal.amount),
        "currency": "NGN",
        "narration": f"TrustPay refund {deal.item_description}",
        "reference": f"refund-{deal.id}",
    }
    pin = getattr(settings, 'PAYAZA_TRANSACTION_PIN', None)
    if pin:
        payload["pin"] = str(pin)
    try:
        resp = requests.post(
            _url("/payout-receptor/payout"),
            json=payload,
            headers=_payaza_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PayazaError(
            "Failed to process refund",
            status_code=getattr(e.response, 'status_code', None),
            response_data=e.response.text if e.response else None,
        ) from e
    return resp.json()


def enquiry_account_name(account_number, bank_code):
    if _mock_mode():
        return {"account_name": "Test Account Holder", "account_number": account_number}
    resp = requests.get(
        _url(f"/payaza-account/api/v1/mainaccounts/merchant/provider/enquiry"),
        params={"account_number": account_number, "bank_code": bank_code},
        headers=_payaza_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def check_transaction_status(reference):
    if _mock_mode():
        return {"status": "success", "transaction_status": "completed", "reference": reference}
    try:
        resp = requests.get(
            _url(f"/payaza-account/api/v1/mainaccounts/merchant/transaction/{reference}"),
            headers=_payaza_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PayazaError(
            "Failed to check transaction status",
            status_code=getattr(e.response, 'status_code', None),
            response_data=e.response.text if e.response else None,
        ) from e
    return resp.json()


def verify_webhook_signature(raw_body, signature_header):
    expected = hmac.new(
        settings.PAYAZA_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.lower())
