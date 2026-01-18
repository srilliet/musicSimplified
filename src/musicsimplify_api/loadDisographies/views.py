import os
import time
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from downloader.models import Track, NewTrack
from artistFetcher.views import fetch_artist_discography_helper


@api_view(['POST'])
def load_all_discographies(request):
    artists = Track.objects.filter(
        artist_name__isnull=False
    ).exclude(
        artist_name=''
    ).values_list('artist_name', flat=True).distinct()
    
    artists = list(artists)
    
    if not artists:
        return Response({
            'message': 'No artists found in database',
            'artists_processed': 0,
            'artists_failed': 0,
            'total_new_tracks': 0
        }, status=status.HTTP_200_OK)
    
    total_new_tracks = 0
    artists_processed = 0
    artists_failed = 0
    
    for i, artist_name in enumerate(artists, 1):
        try:
            result = fetch_artist_discography_helper(artist_name)
            tracks_data = result.get('tracks', [])
            
            if not tracks_data:
                artists_failed += 1
                continue
            
            new_count = 0
            duplicate_count = 0
            
            for track_data in tracks_data:
                track_name = track_data.get('track_name', '')
                album = track_data.get('album', '')
                artist = track_data.get('artist_name', artist_name)
                genre = track_data.get('genre', '')
                
                if track_name and not NewTrack.objects.filter(
                    artist_name=artist,
                    track_name=track_name
                ).exists():
                    NewTrack.objects.create(
                        artist_name=artist,
                        track_name=track_name,
                        album=album if album else None,
                        genre=genre if genre else None
                    )
                    new_count += 1
                else:
                    duplicate_count += 1
            
            total_new_tracks += new_count
            artists_processed += 1
            
            if i < len(artists):
                time.sleep(1)
        
        except Exception as e:
            artists_failed += 1
            continue
    
    return Response({
        'message': 'Processing complete',
        'artists_processed': artists_processed,
        'artists_failed': artists_failed,
        'total_new_tracks': total_new_tracks
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def load_artist_discography(request):
    artist_name = request.data.get('artist_name')
    
    if not artist_name:
        return Response(
            {'error': 'artist_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        result = fetch_artist_discography_helper(artist_name)
        tracks_data = result.get('tracks', [])
        
        new_count = 0
        duplicate_count = 0
        
        for track_data in tracks_data:
            track_name = track_data.get('track_name', '')
            album = track_data.get('album', '')
            artist = track_data.get('artist_name', artist_name)
            genre = track_data.get('genre', '')
            
            if track_name and not NewTrack.objects.filter(
                artist_name=artist,
                track_name=track_name
            ).exists():
                NewTrack.objects.create(
                    artist_name=artist,
                    track_name=track_name,
                    album=album if album else None,
                    genre=genre if genre else None
                )
                new_count += 1
            else:
                duplicate_count += 1
        
        return Response({
            'message': 'Discography loaded successfully',
            'artist_name': artist_name,
            'tracks_found': len(tracks_data),
            'new_tracks': new_count,
            'duplicates': duplicate_count
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Error loading discography: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_new_tracks(request):
    from django.db.models import Q
    
    artist_name = request.query_params.get('artist_name', None)
    search = request.query_params.get('search', None)
    genre = request.query_params.get('genre', None)
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 50)
    
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 50
    
    # Limit page_size to reasonable range
    page_size = min(max(page_size, 1), 100)
    
    # Start with base queryset - exclude downloaded tracks (success=True)
    queryset = NewTrack.objects.filter(success=False).order_by('artist_name', 'track_name')
    
    # Apply filters
    if artist_name:
        queryset = queryset.filter(artist_name=artist_name)
    
    if search:
        # Search in artist_name or track_name (case-insensitive)
        queryset = queryset.filter(
            Q(artist_name__icontains=search) | Q(track_name__icontains=search)
        )
    
    if genre:
        queryset = queryset.filter(genre=genre)
    
    # Calculate pagination
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    page = max(1, min(page, total_pages))  # Clamp page to valid range
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_tracks = queryset[start:end]
    
    tracks = []
    for track in paginated_tracks:
        tracks.append({
            'id': track.id,
            'artist_name': track.artist_name,
            'track_name': track.track_name,
            'album': track.album,
            'genre': track.genre
        })
    
    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'tracks': tracks
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_genres(request):
    """Get list of unique genres from new_tracks table (excluding downloaded tracks)"""
    genres = NewTrack.objects.filter(
        success=False,
        genre__isnull=False
    ).exclude(
        genre=''
    ).values_list('genre', flat=True).distinct().order_by('genre')
    
    return Response({
        'genres': list(genres)
    }, status=status.HTTP_200_OK)
