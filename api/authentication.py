from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Adminn as Admin
import jwt
from django.conf import settings


def get_tokens_for_admin(admin):
    refresh = RefreshToken.for_user(admin)  # ensures USER_ID_CLAIM is present
    refresh["email"] = admin.email
    refresh["college"] = admin.college

    access = refresh.access_token
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
        
        token = auth_header.split(' ')[1] if len(auth_header.split(' ')) > 1 else None
        
        if not token:
            return None
        
        try:
            # Use the same signing key as configured in SIMPLE_JWT
            signing_key = settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY)
            payload = jwt.decode(token, signing_key, algorithms=['HS256'])
            admin = Admin.objects.get(id=payload['id'])
            return (admin, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Admin.DoesNotExist:
            raise AuthenticationFailed('Admin not found')
        except KeyError:
            raise AuthenticationFailed('Invalid token payload')


class CookieJWTAuthentication(BaseAuthentication):
    """Custom authentication to read JWT from cookies"""
    
    def authenticate(self, request):
        token = request.COOKIES.get('token')
        
        if not token:
            return None
        
        try:
            # Use the same signing key as configured in SIMPLE_JWT
            signing_key = settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY)
            payload = jwt.decode(token, signing_key, algorithms=['HS256'])
            admin = Admin.objects.get(id=payload['id'])
            return (admin, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Admin.DoesNotExist:
            raise AuthenticationFailed('Admin not found')
        except KeyError:
            raise AuthenticationFailed('Invalid token payload')
