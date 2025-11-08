from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings  # <-- لاستخراج USER_ID_CLAIM/USER_ID_FIELD
from .models import Adminn as Admin
import jwt
from django.conf import settings


def get_tokens_for_admin(admin):
    """
    ينشئ Refresh/Access tokens وفق SimpleJWT.
    لا حاجة لإضافة claim 'id' يدويًا لأن SimpleJWT يضيف USER_ID_CLAIM تلقائيًا (user_id).
    يمكن إبقاء الإضافات الاختيارية (email/college) كما هي.
    """
    refresh = RefreshToken.for_user(admin)  # يضمن وجود USER_ID_CLAIM

    # claims اختيارية
    refresh["email"] = admin.email
    refresh["college"] = admin.college

    access = refresh.access_token
    # ملاحظة: claims الإضافية لا تُنسخ تلقائيًا من refresh → أضفها يدويًا إن احتجتها داخل access
    access["email"] = admin.email
    access["college"] = admin.college

    return {"refresh": str(refresh), "access": str(access)}


class AdminJWTAuthentication(BaseAuthentication):
    """Custom JWT authentication for Admin model using Bearer tokens"""

    def authenticate(self, request):
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return None

        parts = auth_header.split(' ')
        token = parts[1] if len(parts) > 1 else None

        if not token:
            return None

        try:
            # استخدم نفس الإعدادات في SIMPLE_JWT
            signing_key = settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY)
            algo = settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')

            # فك التوكِن (لا يتحقق من البلاك ليست، فقط التوقيع والصلاحية)
            payload = jwt.decode(token, signing_key, algorithms=[algo])

            # اقرأ claim المعرِّف وفق الإعدادات (افتراضيًا 'user_id')
            claim_name = api_settings.USER_ID_CLAIM
            user_id_field = api_settings.USER_ID_FIELD  # افتراضيًا 'id'
            admin_id = payload.get(claim_name)
            if admin_id is None:
                raise AuthenticationFailed('Invalid token payload')

            admin = Admin.objects.get(**{user_id_field: admin_id})
            return (admin, None)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Admin.DoesNotExist:
            raise AuthenticationFailed('Admin not found')


class CookieJWTAuthentication(BaseAuthentication):
    """Custom authentication to read JWT from cookies"""

    def authenticate(self, request):
        token = request.COOKIES.get('token')

        if not token:
            return None

        try:
            signing_key = settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY)
            algo = settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')

            payload = jwt.decode(token, signing_key, algorithms=[algo])

            claim_name = api_settings.USER_ID_CLAIM
            user_id_field = api_settings.USER_ID_FIELD
            admin_id = payload.get(claim_name)
            if admin_id is None:
                raise AuthenticationFailed('Invalid token payload')

            admin = Admin.objects.get(**{user_id_field: admin_id})
            return (admin, None)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Admin.DoesNotExist:
            raise AuthenticationFailed('Admin not found')
