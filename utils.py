from storage import USERS

def is_vip(user_id: int) -> bool:
    return USERS.get(str(user_id)) == "VIP"