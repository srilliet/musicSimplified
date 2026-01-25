from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AuthToken


class TokenAuthentication(BaseAuthentication):
    """
    Custom token authentication using UUID tokens.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Token '):
            return None
        
        token_str = auth_header.replace('Token ', '')
        
        try:
            token = AuthToken.objects.get(token=token_str, is_active=True)
            return (token.user, token)
        except (AuthToken.DoesNotExist, ValueError):
            raise AuthenticationFailed('Invalid token')
