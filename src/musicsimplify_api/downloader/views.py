import os
import subprocess
import re
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Track


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
        track.download = 1
        track.failed_download = 0
        track.save()
        return {'success': True, 'file_path': file_path, 'method': 'yt-dlp'}
    
    file_path = download_with_spotdl(
        track.track_name,
        track.artist_name,
        track.album,
        download_dir
    )
    
    if file_path:
        track.download = 1
        track.failed_download = 0
        track.save()
        return {'success': True, 'file_path': file_path, 'method': 'spotdl'}
    
    track.failed_download = 1
    track.save()
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
    undownloaded_only = request.query_params.get('undownloaded_only', 'false').lower() == 'true'
    limit = request.query_params.get('limit', None)
    
    queryset = Track.objects.all()
    
    if undownloaded_only:
        queryset = queryset.filter(download=0, failed_download=0)
    
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
            'download': track.download,
            'failed_download': track.failed_download
        })
    
    return Response({
        'count': len(tracks),
        'tracks': tracks
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_undownloaded_count(request):
    count = Track.objects.filter(download=0, failed_download=0).count()
    return Response({
        'count': count
    }, status=status.HTTP_200_OK)
