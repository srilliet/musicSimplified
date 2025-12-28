import os
import subprocess
import re
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Track, Settings


def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    return filename


def download_with_ytdlp(track_name, artist_name, album, download_dir):
    try:
        search_query = f"{artist_name} {track_name}"
        sanitized_artist = sanitize_filename(artist_name) if artist_name else "Unknown Artist"
        sanitized_album = sanitize_filename(album) if album else "Unknown Album"
        sanitized_track = sanitize_filename(track_name)
        
        output_dir = Path(download_dir) / sanitized_artist / sanitized_album
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_dir / f"{sanitized_track}.%(ext)s")
        
        ytdlp_cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '0',
            '--default-search', 'ytsearch',
            '--output', output_template,
            '--no-playlist',
            '--quiet',
            '--no-warnings',
            f'ytsearch1:{search_query}'
        ]
        
        result = subprocess.run(
            ytdlp_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            mp3_file = output_dir / f"{sanitized_track}.mp3"
            if mp3_file.exists():
                return str(mp3_file)
        
        return None
    except Exception as e:
        return None


def download_with_spotdl(track_name, artist_name, album, download_dir):
    original_cwd = os.getcwd()
    try:
        search_query = f"{artist_name} {track_name}"
        sanitized_artist = sanitize_filename(artist_name) if artist_name else "Unknown Artist"
        sanitized_album = sanitize_filename(album) if album else "Unknown Album"
        
        output_dir = Path(download_dir) / sanitized_artist / sanitized_album
        output_dir.mkdir(parents=True, exist_ok=True)
        
        os.chdir(str(output_dir))
        
        spotdl_cmd = [
            'spotdl',
            'download',
            search_query,
            '--format', 'mp3',
            '--output', '{artist} - {title}.{ext}'
        ]
        
        result = subprocess.run(
            spotdl_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            for file in output_dir.glob("*.mp3"):
                return str(file)
        
        return None
    except Exception as e:
        return None
    finally:
        os.chdir(original_cwd)


def download_track_helper(track_id, download_dir=None):
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return {'success': False, 'error': 'Track not found'}
    
    if not download_dir:
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        download_dir = str(project_root / 'downloads')
    
    file_path = download_with_ytdlp(
        track.track_name,
        track.artist_name,
        track.album,
        download_dir
    )
    
    if file_path:
        track.save()
        return {'success': True, 'file_path': file_path, 'method': 'yt-dlp'}
    
    file_path = download_with_spotdl(
        track.track_name,
        track.artist_name,
        track.album,
        download_dir
    )
    
    if file_path:
        track.save()
        return {'success': True, 'file_path': file_path, 'method': 'spotdl'}
    
    return {'success': False, 'error': 'Download failed with both methods'}


@api_view(['POST'])
def download_track(request):
    track_id = request.data.get('track_id')
    download_dir = request.data.get('download_dir', None)
    
    if not track_id:
        return Response(
            {'error': 'track_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = download_track_helper(track_id, download_dir)
    
    if result.get('success'):
        return Response({
            'success': True,
            'message': 'Download successful',
            'file_path': result.get('file_path'),
            'method': result.get('method')
        }, status=status.HTTP_200_OK)
    else:
        error_msg = result.get('error', 'Download failed')
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in error_msg.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({
            'success': False,
            'message': error_msg
        }, status=status_code)


@api_view(['GET'])
def get_tracks(request):
    limit = request.query_params.get('limit', None)
    
    queryset = Track.objects.all()
    
    if limit:
        try:
            limit = int(limit)
            queryset = queryset[:limit]
        except ValueError:
            pass
    
    tracks = []
    for track in queryset:
        tracks.append({
            'id': track.id,
            'track_name': track.track_name,
            'album': track.album,
            'artist_name': track.artist_name,
            'genre': track.genre,
            'relative_path': track.relative_path
        })
    
    return Response({
        'count': len(tracks),
        'tracks': tracks
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_undownloaded_count(request):
    # This endpoint is deprecated as download tracking fields have been removed
    count = Track.objects.count()
    return Response({
        'count': count,
        'message': 'Download tracking fields have been removed. This endpoint returns total track count.'
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
def get_or_update_settings(request):
    """
    Get or update application settings.
    GET: Returns current settings
    PUT: Updates settings (requires 'root_music_path' in request data)
    """
    settings = Settings.get_settings()
    
    if request.method == 'GET':
        return Response({
            'id': settings.id,
            'root_music_path': settings.root_music_path,
            'updated_at': settings.updated_at
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        root_music_path = request.data.get('root_music_path')
        
        if not root_music_path:
            return Response(
                {'error': 'root_music_path is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        settings.root_music_path = root_music_path
        settings.save()
        
        return Response({
            'id': settings.id,
            'root_music_path': settings.root_music_path,
            'updated_at': settings.updated_at,
            'message': 'Settings updated successfully'
        }, status=status.HTTP_200_OK)
