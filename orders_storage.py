import json
import os

FILE_NAME = "orders.json"

def load_orders():
    if not os.path.exists(FILE_NAME):
        return {}

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders: dict):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)