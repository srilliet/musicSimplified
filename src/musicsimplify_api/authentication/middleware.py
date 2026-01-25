from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import AuthToken


class TokenAuthenticationMiddleware(MiddlewareMixin):
    """
    Custom middleware to authenticate users via UUID tokens in the Authorization header.
    """
    def process_request(self, request):
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Token '):
            token_str = auth_header.replace('Token ', '')
            
            try:
                token = AuthToken.objects.get(token=token_str, is_active=True)
                request.user = token.user
            except (AuthToken.DoesNotExist, ValueError):
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
