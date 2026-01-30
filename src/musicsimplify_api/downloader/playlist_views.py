from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Playlist, PlaylistTrack, Track


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_playlists(request):
    """
    Get all playlists for the authenticated user.
    """
    user = request.user
    
    playlists = Playlist.objects.filter(user=user).order_by('-created_at')
    
    playlist_list = []
    for playlist in playlists:
        playlist_list.append({
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description,
            'created_at': playlist.created_at.isoformat(),
            'updated_at': playlist.updated_at.isoformat(),
            'track_count': playlist.playlist_tracks.count()
        })
    
    return Response({
        'playlists': playlist_list,
        'count': len(playlist_list)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_playlist(request):
    """
    Create a new playlist for the authenticated user.
    """
    user = request.user
    
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Playlist name is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    description = request.data.get('description', '').strip() or None
    
    # Create the playlist
    playlist = Playlist.objects.create(
        user=user,
        name=name,
        description=description
    )
    
    return Response({
        'message': 'Playlist created successfully',
        'playlist': {
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description,
            'created_at': playlist.created_at.isoformat(),
            'updated_at': playlist.updated_at.isoformat(),
            'track_count': 0
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_playlist(request, playlist_id):
    """
    Delete a playlist (only if it belongs to the authenticated user).
    """
    user = request.user
    
    try:
        playlist = Playlist.objects.get(id=playlist_id, user=user)
    except Playlist.DoesNotExist:
        return Response({'error': 'Playlist not found'}, status=status.HTTP_404_NOT_FOUND)
    
    playlist_name = playlist.name
    playlist.delete()
    
    return Response({
        'message': f'Playlist "{playlist_name}" deleted successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_tracks_to_playlist(request, playlist_id):
    """
    Add multiple tracks to a playlist.
    """
    user = request.user
    
    try:
        playlist = Playlist.objects.get(id=playlist_id, user=user)
    except Playlist.DoesNotExist:
        return Response({'error': 'Playlist not found'}, status=status.HTTP_404_NOT_FOUND)
    
    track_ids = request.data.get('track_ids', [])
    
    if not track_ids or not isinstance(track_ids, list):
        return Response(
            {'error': 'track_ids array is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get the current maximum position in the playlist
    max_position = PlaylistTrack.objects.filter(playlist=playlist).aggregate(
        max_pos=models.Max('position')
    )['max_pos'] or -1
    
    added_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for track_id in track_ids:
        try:
            track = Track.objects.get(id=track_id)
        except Track.DoesNotExist:
            not_found_count += 1
            continue
        
        # Check if track already exists in playlist
        existing = PlaylistTrack.objects.filter(playlist=playlist, track=track).first()
        if existing:
            skipped_count += 1
            continue
        
        # Add track to playlist
        max_position += 1
        PlaylistTrack.objects.create(
            playlist=playlist,
            track=track,
            position=max_position
        )
        added_count += 1
    
    return Response({
        'message': f'Added {added_count} tracks to playlist',
        'added': added_count,
        'skipped': skipped_count,
        'not_found': not_found_count,
        'total_requested': len(track_ids)
    }, status=status.HTTP_200_OK)
