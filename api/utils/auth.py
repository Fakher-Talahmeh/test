# utils/auth.py
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings  # to read USER_ID_CLAIM if needed

def get_tokens_for_admin(admin: "Adminn"):
    refresh = RefreshToken.for_user(admin)  # <-- ensures USER_ID_CLAIM is present

    # optional extra claims
    refresh["email"] = admin.email
    refresh["college"] = admin.college

    access = refresh.access_token
    # extra claims do NOT automatically copy from refresh → add if you need them on access too
    access["email"] = admin.email
    access["college"] = admin.college

    return {
        "refresh": str(refresh),
        "access": str(access),
    }
