# auth_backends.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from .models import Adminn as Admin

class AdminJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if not user_id:
            self.fail("no_user_id")

        try:
            return Admin.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except Admin.DoesNotExist:
            self.fail("user_not_found")
