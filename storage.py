import json
import os

USERS_FILE = "users.json"
PROMO_FILE = "promo_codes.json"
ORDERS_FILE = "orders.json"

def load_json(file_name):
    if not os.path.exists(file_name):
        return {}
    with open(file_name, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_vip(user_id: int) -> bool:
    return USERS.get(str(user_id), "USER") == "VIP"



USERS = load_json(USERS_FILE)
PROMO_CODES = load_json(PROMO_FILE)




try:
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        ORDERS = json.load(f)
except:
    ORDERS = {}


def save_orders(data):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
