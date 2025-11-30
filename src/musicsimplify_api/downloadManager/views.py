import time
import math
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from downloader.models import Track
from downloader.views import download_track_helper


def calculate_delay(total_tracks):
    if total_tracks <= 10:
        return 1.0
    elif total_tracks <= 100:
        return 2.0
    elif total_tracks <= 500:
        return 3.0 + (total_tracks / 100)
    else:
        base_delay = 5.0
        log_factor = math.log10(total_tracks / 100)
        return min(base_delay + log_factor * 2, 10.0)


@api_view(['POST'])
def download_all_tracks(request):
    download_dir = request.data.get('download_dir', None)
    limit = request.data.get('limit', None)
    
    if not download_dir:
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        download_dir = str(project_root / 'downloads')
    
    total_tracks = Track.objects.filter(download=0, failed_download=0).count()
    
    if total_tracks == 0:
        return Response({
            'message': 'No tracks to download',
            'successful': 0,
            'failed': 0
        }, status=status.HTTP_200_OK)
    
    if limit:
        try:
            limit = int(limit)
            total_tracks = min(total_tracks, limit)
        except ValueError:
            limit = None
    
    tracks = Track.objects.filter(download=0, failed_download=0).order_by('id')
    if limit:
        tracks = tracks[:limit]
    
    delay = calculate_delay(total_tracks)
    
    successful = 0
    failed = 0
    
    for i, track in enumerate(tracks, 1):
        try:
            result = download_track_helper(track.id, download_dir)
            if result.get('success'):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
        
        if i < total_tracks:
            time.sleep(delay)
    
    return Response({
        'message': 'Download complete',
        'total': total_tracks,
        'successful': successful,
        'failed': failed,
        'delay_used': delay
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_download_stats(request):
    total_tracks = Track.objects.count()
    downloaded = Track.objects.filter(download=1).count()
    failed = Track.objects.filter(failed_download=1).count()
    undownloaded = Track.objects.filter(download=0, failed_download=0).count()
    
    return Response({
        'total_tracks': total_tracks,
        'downloaded': downloaded,
        'failed': failed,
        'undownloaded': undownloaded
    }, status=status.HTTP_200_OK)
