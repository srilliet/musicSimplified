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
    
    spotify_configured = bool(os.getenv('SPOTIFY_CLIENT_ID') and os.getenv('SPOTIFY_CLIENT_SECRET'))
    
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
                
                if track_name and not NewTrack.objects.filter(
                    artist_name=artist,
                    track_name=track_name
                ).exists():
                    NewTrack.objects.create(
                        artist_name=artist,
                        track_name=track_name,
                        album=album if album else None
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
        'total_new_tracks': total_new_tracks,
        'spotify_configured': spotify_configured
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
            
            if track_name and not NewTrack.objects.filter(
                artist_name=artist,
                track_name=track_name
            ).exists():
                NewTrack.objects.create(
                    artist_name=artist,
                    track_name=track_name,
                    album=album if album else None
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
    artist_name = request.query_params.get('artist_name', None)
    
    if artist_name:
        new_tracks = NewTrack.objects.filter(artist_name=artist_name).order_by('track_name')
    else:
        new_tracks = NewTrack.objects.all().order_by('artist_name', 'track_name')
    
    tracks = []
    for track in new_tracks:
        tracks.append({
            'id': track.id,
            'artist_name': track.artist_name,
            'track_name': track.track_name,
            'album': track.album
        })
    
    return Response({
        'count': len(tracks),
        'tracks': tracks
    }, status=status.HTTP_200_OK)
