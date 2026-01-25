from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import AuthToken
import uuid


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Deactivate old tokens for this user
    AuthToken.objects.filter(user=user, is_active=True).update(is_active=False)
    
    # Create new token
    token = AuthToken.objects.create(user=user)
    
    return Response({
        'token': str(token.token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Token '):
        return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    token_str = auth_header.replace('Token ', '')
    
    try:
        token = AuthToken.objects.get(token=token_str, is_active=True)
        token.is_active = False
        token.save()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except AuthToken.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email
        }
    }, status=status.HTTP_200_OK)
