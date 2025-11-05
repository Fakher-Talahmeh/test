from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Adminn as Admin
import jwt
from django.conf import settings


def get_tokens_for_admin(admin):
    """Generate JWT tokens for admin"""
    refresh = RefreshToken()
    refresh['id'] = admin.id
    refresh['email'] = admin.email
    refresh['college'] = admin.college
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class CookieJWTAuthentication(BaseAuthentication):
    """Custom authentication to read JWT from cookies"""
    
    def authenticate(self, request):
        token = request.COOKIES.get('token')
        
        if not token:
            return None
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            admin = Admin.objects.get(id=payload['id'])
            return (admin, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Admin.DoesNotExist:
            raise AuthenticationFailed('Admin not found')
