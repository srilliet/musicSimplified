from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from .models import Track, UserTrack


@api_view(['POST'])
def initialize_user_library(request):
    """
    Initialize user's library with all tracks from the global tracks table.
    This is called automatically when user first accesses their library.
    """
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get all tracks
    all_tracks = Track.objects.all()
    
    # Get existing user tracks
    existing_user_tracks = UserTrack.objects.filter(user=user).values_list('track_id', flat=True)
    existing_track_ids = set(existing_user_tracks)
    
    # Create UserTrack entries for tracks that don't have one yet
    new_user_tracks = []
    for track in all_tracks:
        if track.id not in existing_track_ids:
            new_user_tracks.append(
                UserTrack(user=user, track=track, is_removed=False)
            )
    
    if new_user_tracks:
        UserTrack.objects.bulk_create(new_user_tracks, ignore_conflicts=True)
    
    return Response({
        'message': 'Library initialized successfully',
        'tracks_added': len(new_user_tracks),
        'total_tracks': all_tracks.count()
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_tracks(request):
    """
    Get user's library tracks (all tracks minus removed ones).
    Includes user-specific playcount and skipcount.
    """
    from django.db.models import Q
    
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Ensure library is initialized
    all_track_ids = set(Track.objects.values_list('id', flat=True))
    user_track_ids = set(UserTrack.objects.filter(user=user).values_list('track_id', flat=True))
    missing_track_ids = all_track_ids - user_track_ids
    
    if missing_track_ids:
        # Initialize missing tracks
        new_user_tracks = [
            UserTrack(user=user, track_id=track_id, is_removed=False)
            for track_id in missing_track_ids
        ]
        UserTrack.objects.bulk_create(new_user_tracks, ignore_conflicts=True)
    
    # Get query parameters
    artist_name = request.query_params.get('artist_name', None)
    search = request.query_params.get('search', None)
    genre = request.query_params.get('genre', None)
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 100)
    
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 100
    
    # Limit page_size to reasonable range
    page_size = min(max(page_size, 1), 100)
    
    # Start with user tracks that are not removed
    queryset = UserTrack.objects.filter(
        user=user,
        is_removed=False
    ).select_related('track').order_by('track__artist_name', 'track__track_name')
    
    # Apply filters
    if artist_name:
        queryset = queryset.filter(track__artist_name=artist_name)
    
    if search:
        queryset = queryset.filter(
            Q(track__artist_name__icontains=search) | Q(track__track_name__icontains=search)
        )
    
    if genre:
        queryset = queryset.filter(track__genre=genre)
    
    # Calculate pagination
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size
    page = max(1, min(page, total_pages))
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_user_tracks = queryset[start:end]
    
    tracks = []
    for user_track in paginated_user_tracks:
        track = user_track.track
        tracks.append({
            'id': track.id,
            'artist_name': track.artist_name,
            'track_name': track.track_name,
            'album': track.album,
            'genre': track.genre,
            'relative_path': track.relative_path,
            'playcount': user_track.playcount,
            'skipcount': user_track.skipcount,
            'rating': user_track.rating,
            'favorite': user_track.favorite,
            'last_played': user_track.last_played.isoformat() if user_track.last_played else None,
            'play_streak': user_track.play_streak,
        })
    
    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'tracks': tracks
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def remove_track_from_library(request, track_id):
    """Remove a track from user's library"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get or create UserTrack entry
    user_track, created = UserTrack.objects.get_or_create(
        user=user,
        track=track,
        defaults={'is_removed': False}
    )
    
    # Mark as removed
    user_track.is_removed = True
    user_track.removed_at = timezone.now()
    user_track.save()
    
    return Response({
        'message': 'Track removed from library',
        'track_id': track_id
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def restore_track_to_library(request, track_id):
    """Restore a track to user's library"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get or create UserTrack entry
    user_track, created = UserTrack.objects.get_or_create(
        user=user,
        track=track,
        defaults={'is_removed': False}
    )
    
    # Restore to library
    user_track.is_removed = False
    user_track.removed_at = None
    user_track.save()
    
    return Response({
        'message': 'Track restored to library',
        'track_id': track_id
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_tracks_genres(request):
    """Get list of unique genres from user's library"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    genres = UserTrack.objects.filter(
        user=user,
        is_removed=False,
        track__genre__isnull=False
    ).exclude(
        track__genre=''
    ).values_list('track__genre', flat=True).distinct().order_by('track__genre')
    
    return Response({
        'genres': list(genres)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_tracks_artists(request):
    """Get list of unique artists from user's library"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    artists = UserTrack.objects.filter(
        user=user,
        is_removed=False,
        track__artist_name__isnull=False
    ).exclude(
        track__artist_name=''
    ).values_list('track__artist_name', flat=True).distinct().order_by('track__artist_name')
    
    return Response({
        'artists': list(artists)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_removed_tracks(request):
    """Get tracks that user has removed from their library"""
    from django.db.models import Q
    
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get query parameters
    search = request.query_params.get('search', None)
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 100)
    
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 100
    
    # Limit page_size to reasonable range
    page_size = min(max(page_size, 1), 100)
    
    # Get removed tracks
    queryset = UserTrack.objects.filter(
        user=user,
        is_removed=True
    ).select_related('track').order_by('-removed_at', 'track__artist_name', 'track__track_name')
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            Q(track__artist_name__icontains=search) | Q(track__track_name__icontains=search)
        )
    
    # Calculate pagination
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size
    page = max(1, min(page, total_pages))
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_user_tracks = queryset[start:end]
    
    tracks = []
    for user_track in paginated_user_tracks:
        track = user_track.track
        tracks.append({
            'id': track.id,
            'artist_name': track.artist_name,
            'track_name': track.track_name,
            'album': track.album,
            'genre': track.genre,
            'relative_path': track.relative_path,
            'removed_at': user_track.removed_at.isoformat() if user_track.removed_at else None,
        })
    
    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'tracks': tracks
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def restore_all_tracks(request):
    """Restore all removed tracks to user's library"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get all removed tracks for this user
    removed_tracks = UserTrack.objects.filter(user=user, is_removed=True)
    count = removed_tracks.count()
    
    # Restore all tracks
    removed_tracks.update(is_removed=False, removed_at=None)
    
    return Response({
        'message': f'Restored {count} tracks to library',
        'count': count
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
def update_user_track(request, track_id):
    """Update user track fields (rating, favorite, etc.)"""
    user = request.user
    
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get or create UserTrack entry
    user_track, created = UserTrack.objects.get_or_create(
        user=user,
        track=track,
        defaults={'is_removed': False}
    )
    
    # Update fields if provided
    if 'rating' in request.data:
        rating = request.data.get('rating')
        if rating is None or (isinstance(rating, int) and 1 <= rating <= 5):
            user_track.rating = rating
        else:
            return Response({'error': 'Rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'favorite' in request.data:
        user_track.favorite = bool(request.data.get('favorite'))
    
    user_track.save()
    
    return Response({
        'message': 'Track updated successfully',
        'track_id': track_id,
        'rating': user_track.rating,
        'favorite': user_track.favorite
    }, status=status.HTTP_200_OK)
