import requests

CRYPTO_PAY_TOKEN = "517120:AA0vZHUAZJfuHSc6ma2jTZWNn2KnCNuqGaY"
API_URL = "https://pay.crypt.bot/api"


def create_invoice(amount: int, order_id: str):
    r = requests.post(
        f"{API_URL}/createInvoice",
        headers={
            "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
        },
        json={
            "asset": "USDT",
            "amount": str(amount),
            "description": f"Оплата заказа {order_id}"
        }
    )

    data = r.json()
    if not data.get("ok"):
        raise Exception(data)

    return data["result"]


def check_invoice(invoice_id: int):
    r = requests.get(
        f"{API_URL}/getInvoices",
        headers={
            "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
        },
        params={"invoice_ids": invoice_id}
    )

    data = r.json()
    if not data.get("ok"):
        return None

    invoices = data["result"]["items"]
    return invoices[0] if invoices else None
