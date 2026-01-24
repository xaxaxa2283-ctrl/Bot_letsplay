from storage import is_vip

# ----------------------------
# SUBSCRIPTIONS (подписки)
# ----------------------------

VIP_PRICES = {
    "Турция": {
        "1 месяц": {
            "Plus Deluxe": 1400,
            "Plus Extra": 1225,
            "EA Play": 830
        },
        "3 месяца": {
            "Plus Deluxe": 3200,
            "Plus Extra": 2800,
            "EA Play": 2700
        },
        "1 год": {
            "Plus Deluxe": 9250,
            "Plus Extra": 8020,
            "EA Play": 3550
        }
    },
    "СНГ": {
        "1 месяц": {
            "Plus Deluxe": 1425,
            "Plus Extra": 1300,
            "EA Play": 830
        },
        "3 месяца": {
            "Plus Deluxe": 2800,
            "Plus Extra": 2450,
            "EA Play": 1700
        },
        "1 год": {
            "Plus Deluxe": 6120,
            "Plus Extra": 5350,
            "EA Play": 2230
        }
    }
}

PRICES = {
    "Турция": {
        "1 месяц": {
            "Plus Deluxe": 2900,
            "Plus Extra": 2490,
            "EA Play": 1390
        },
        "3 месяца": {
            "Plus Deluxe": 6700,
            "Plus Extra": 2800,
            "EA Play": 3700
        },
        "1 год": {
            "Plus Deluxe": 13500,
            "Plus Extra": 11900,
            "EA Play": 7500
        }
    },
    "СНГ": {
        "1 месяц": {
            "Plus Deluxe": 3500,
            "Plus Extra": 2500,
            "EA Play": 1500
        },
        "3 месяца": {
            "Plus Deluxe": 5490,
            "Plus Extra": 4900,
            "EA Play": 2900
        },
        "1 год": {
            "Plus Deluxe": 10900,
            "Plus Extra": 9900,
            "EA Play": 5990
        }
    }
}

def get_price(user_id, region, period, sub_type):
    prices = VIP_PRICES if is_vip(user_id) else PRICES
    try:
        return prices[region][period][sub_type]
    except KeyError:
        raise ValueError(f"Цена не найдена: {region} / {period} / {sub_type}")


# ----------------------------
# TOPUP (пополнение аккаунта)
# ----------------------------

TOPUP_CURRENCY = {
    "СНГ": "₽",
    "Турция": "₺",
}

# fee = фиксированная комиссия в валюте региона
VIP_TOPUP = {
    "СНГ": [
        {"from": 0, "to": 999, "fee": 50},
        {"from": 1000, "to": 2999, "fee": 80},
        {"from": 3000, "to": 9999999, "fee": 120},
    ],
    "Турция": [
        {"from": 0, "to": 999, "fee": 20},
        {"from": 1000, "to": 2999, "fee": 35},
        {"from": 3000, "to": 9999999, "fee": 50},
    ],
}

TOPUP = {
    "СНГ": [
        {"from": 0, "to": 999, "fee": 150},
        {"from": 1000, "to": 2999, "fee": 200},
        {"from": 3000, "to": 9999999, "fee": 300},
    ],
    "Турция": [
        {"from": 0, "to": 999, "fee": 60},
        {"from": 1000, "to": 2999, "fee": 90},
        {"from": 3000, "to": 9999999, "fee": 120},
    ],
}

def get_topup_fee(user_id, region, amount: float) -> float:
    tables = VIP_TOPUP if is_vip(user_id) else TOPUP
    tiers = tables.get(region, [])
    for t in tiers:
        if t["from"] <= amount <= t["to"]:
            return float(t["fee"])
    return 0.0

def calc_topup_total(user_id, region, amount: float) -> float:
    return float(amount) + get_topup_fee(user_id, region, amount)
