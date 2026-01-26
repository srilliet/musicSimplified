import os
import time
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from downloader.models import Track, NewTrack
from artistFetcher.views import fetch_artist_discography_helper
import musicbrainzngs

logger = logging.getLogger(__name__)


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


def get_artist_genre_musicbrainz(artist_name):
    """
    Fetch genre for an artist from MusicBrainz API.
    
    Args:
        artist_name (str): Name of the artist
        
    Returns:
        str: Primary genre or None if not found
    """
    try:
        musicbrainzngs.set_useragent("MusicSimplify", "1.0", "https://github.com/srilliet/musicSimplified")
        
        # Search for artist
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        time.sleep(1)  # Rate limit: 1 second between API calls
        
        if not result.get('artist-list'):
            return None
        
        artist = result['artist-list'][0]
        artist_id = artist.get('id')
        
        if not artist_id:
            return None
        
        # Get detailed artist info with tags
        time.sleep(1)  # Rate limit: 1 second between API calls
        try:
            artist_info = musicbrainzngs.get_artist_by_id(artist_id, includes=['tags'])
            
            if 'tag-list' in artist_info.get('artist', {}):
                tags = artist_info['artist']['tag-list']
                if isinstance(tags, list) and len(tags) > 0:
                    # Filter out non-genre tags (country names, years, etc.)
                    non_genre_keywords = ['american', 'british', 'canadian', 'german', 'french', 
                                         'swedish', 'norwegian', 'japanese', 'australian', 'italian',
                                         'spanish', 'dutch', 'polish', 'russian', 'brazilian',
                                         'mexican', 'irish', 'scottish', 'welsh', 'english']
                    
                    genre_tags = []
                    for tag in tags:
                        if isinstance(tag, dict):
                            tag_name = tag.get('name', '').lower()
                            tag_count = int(tag.get('count', 0))
                            # Skip if it's a non-genre keyword
                            if tag_name not in non_genre_keywords:
                                genre_tags.append((tag_name, tag_count))
                    
                    # Sort by count (descending) and return the most popular genre
                    if genre_tags:
                        genre_tags.sort(key=lambda x: x[1], reverse=True)
                        return genre_tags[0][0].title()  # Return capitalized genre name
        except Exception as e:
            logger.debug(f"Error getting artist tags: {e}")
            pass
        
        return None
    except Exception as e:
        logger.error(f"Error fetching artist genre from MusicBrainz for {artist_name}: {e}")
        return None


@api_view(['POST'])
def load_artist_discography(request):
    artist_name = request.data.get('artist_name')
    
    if not artist_name:
        return Response(
            {'error': 'artist_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Fetch artist genre first (will be used as default for tracks without genre)
        logger.info(f"Fetching artist genre for: {artist_name}")
        artist_genre = get_artist_genre_musicbrainz(artist_name)
        logger.info(f"Artist genre for {artist_name}: {artist_genre}")
        
        # Fetch discography
        result = fetch_artist_discography_helper(artist_name)
        tracks_data = result.get('tracks', [])
        
        new_count = 0
        duplicate_count = 0
        updated_count = 0
        
        for track_data in tracks_data:
            track_name = track_data.get('track_name', '')
            album = track_data.get('album', '')
            artist = track_data.get('artist_name', artist_name)
            track_genre = track_data.get('genre', '')
            
            # Use track genre if available, otherwise use artist genre
            final_genre = track_genre if track_genre else artist_genre
            
            if track_name:
                # Check if track already exists
                existing_track = NewTrack.objects.filter(
                    artist_name=artist,
                    track_name=track_name
                ).first()
                
                if existing_track:
                    # Update genre if it's missing (NULL or empty) and we have one
                    current_genre = existing_track.genre
                    if (not current_genre or current_genre.strip() == '') and final_genre:
                        existing_track.genre = final_genre
                        existing_track.save()
                        updated_count += 1
                    duplicate_count += 1
                else:
                    # Create new track
                    NewTrack.objects.create(
                        artist_name=artist,
                        track_name=track_name,
                        album=album if album else None,
                        genre=final_genre if final_genre else None
                    )
                    new_count += 1
        
        return Response({
            'message': 'Discography loaded successfully',
            'artist_name': artist_name,
            'tracks_found': len(tracks_data),
            'new_tracks': new_count,
            'duplicates': duplicate_count,
            'updated': updated_count,
            'artist_genre': artist_genre
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error loading discography for {artist_name}: {e}")
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


@api_view(['GET'])
def get_artists(request):
    """Get list of unique artists from new_tracks table (excluding downloaded tracks)"""
    artists = NewTrack.objects.filter(
        success=False,
        artist_name__isnull=False
    ).exclude(
        artist_name=''
    ).values_list('artist_name', flat=True).distinct().order_by('artist_name')
    
    return Response({
        'artists': list(artists)
    }, status=status.HTTP_200_OK)


def safe_unicode_string(text):
    """Safely handle Unicode strings, removing invalid surrogates."""
    if text is None:
        return None
    try:
        text.encode('utf-8', errors='strict')
        return text
    except (UnicodeEncodeError, AttributeError, TypeError):
        text = str(text)
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')


def download_track_from_newtrack(new_track, download_dir, root_music_path):
    """
    Download a track from NewTrack table using the comprehensive logic from the script.
    
    Returns:
        dict: Result with 'success', 'file_path', 'method', 'error', 'relative_path'
    """
    from downloader.views import download_with_ytdlp, download_with_spotdl
    from pathlib import Path
    
    track_name = new_track.track_name
    artist_name = new_track.artist_name
    album = new_track.album
    
    # Try yt-dlp first
    file_path = download_with_ytdlp(track_name, artist_name, album, download_dir)
    
    if file_path:
        # Verify file actually exists and has content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                'success': False,
                'error': 'File not found after download'
            }
        
        file_size = file_path_obj.stat().st_size
        if file_size == 0:
            return {
                'success': False,
                'error': 'Downloaded file is empty'
            }
        
        # Calculate relative path from root_music_path
        try:
            relative_path = os.path.relpath(file_path, root_music_path)
            relative_path = safe_unicode_string(relative_path)
        except:
            relative_path = None
        
        return {
            'success': True,
            'file_path': file_path,
            'method': 'yt-dlp',
            'relative_path': relative_path
        }
    
    # Try spotdl as fallback
    file_path = download_with_spotdl(track_name, artist_name, album, download_dir)
    
    if file_path:
        # Verify file actually exists and has content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                'success': False,
                'error': 'File not found after download'
            }
        
        file_size = file_path_obj.stat().st_size
        if file_size == 0:
            return {
                'success': False,
                'error': 'Downloaded file is empty'
            }
        
        # Calculate relative path from root_music_path
        try:
            relative_path = os.path.relpath(file_path, root_music_path)
            relative_path = safe_unicode_string(relative_path)
        except:
            relative_path = None
        
        return {
            'success': True,
            'file_path': file_path,
            'method': 'spotdl',
            'relative_path': relative_path
        }
    
    return {
        'success': False,
        'error': 'Download failed with both methods'
    }


def find_or_create_track(new_track, relative_path):
    """
    Find existing track or create new one in tracks table.
    
    Args:
        new_track (NewTrack): NewTrack instance
        relative_path (str): Relative path to the file
        
    Returns:
        Track: Track instance
    """
    # Try to find existing track by relative_path
    if relative_path:
        existing = Track.objects.filter(relative_path=relative_path).first()
        if existing:
            return existing
    
    # Try to find by artist + track name
    existing = Track.objects.filter(
        artist_name__iexact=new_track.artist_name,
        track_name__iexact=new_track.track_name
    ).first()
    
    if existing:
        # Update with relative_path if missing
        if relative_path and not existing.relative_path:
            existing.relative_path = safe_unicode_string(relative_path)
            existing.save()
        return existing
    
    # Create new track
    track = Track(
        track_name=safe_unicode_string(new_track.track_name),
        artist_name=safe_unicode_string(new_track.artist_name),
        album=safe_unicode_string(new_track.album) if new_track.album else None,
        genre=safe_unicode_string(new_track.genre) if new_track.genre else None,
        relative_path=safe_unicode_string(relative_path) if relative_path else None
    )
    track.save()
    return track


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def download_selected_tracks(request):
    """
    Download multiple NewTrack objects by their IDs.
    Uses comprehensive download logic from the script.
    """
    from downloader.models import Settings
    
    track_ids = request.data.get('track_ids', [])
    
    if not track_ids or not isinstance(track_ids, list):
        return Response(
            {'error': 'track_ids array is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get download directory from settings
    settings = Settings.get_settings()
    download_dir = settings.root_music_path
    root_music_path = settings.root_music_path
    
    if not download_dir:
        return Response(
            {'error': 'Download directory not configured in settings'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    successful = 0
    failed = 0
    skipped = 0
    results = []
    total_tracks = len(track_ids)
    
    for i, track_id in enumerate(track_ids, 1):
        try:
            new_track = NewTrack.objects.get(id=track_id)
        except NewTrack.DoesNotExist:
            failed += 1
            results.append({
                'track_id': track_id,
                'success': False,
                'error': 'Track not found',
                'progress': {
                    'current': i,
                    'total': total_tracks,
                    'track_name': 'Unknown'
                }
            })
            continue
        
        track_name = new_track.track_name
        artist_name = new_track.artist_name
        
        # Skip if already successfully downloaded
        if new_track.success:
            skipped += 1
            results.append({
                'track_id': track_id,
                'success': False,
                'error': 'Track already downloaded',
                'skipped': True,
                'progress': {
                    'current': i,
                    'total': total_tracks,
                    'track_name': track_name,
                    'artist_name': artist_name
                }
            })
            continue
        
        # Mark as downloaded (attempted)
        new_track.downloaded = True
        new_track.save()
        
        # Download the track
        result = download_track_from_newtrack(new_track, download_dir, root_music_path)
        
        if result.get('success'):
            # Update new_tracks table - mark as successfully downloaded
            new_track.success = True
            new_track.downloaded = True
            new_track.save()
            
            # Refresh from database to ensure changes are committed
            new_track.refresh_from_db()
            
            # Update or create track in tracks table
            relative_path = result.get('relative_path')
            track = find_or_create_track(new_track, relative_path)
            
            successful += 1
            results.append({
                'track_id': track_id,
                'success': True,
                'file_path': result.get('file_path'),
                'method': result.get('method'),
                'relative_path': relative_path,
                'track_id_created': track.id,
                'progress': {
                    'current': i,
                    'total': total_tracks,
                    'track_name': track_name,
                    'artist_name': artist_name
                }
            })
        else:
            new_track.success = False
            new_track.save()
            failed += 1
            error = result.get('error', 'Unknown error')
            results.append({
                'track_id': track_id,
                'success': False,
                'error': error,
                'progress': {
                    'current': i,
                    'total': total_tracks,
                    'track_name': track_name,
                    'artist_name': artist_name
                }
            })
        
        # Rate limiting - wait between downloads (except for the last one)
        if i < len(track_ids):
            time.sleep(2)  # 2 second delay between downloads
    
    return Response({
        'message': f'Downloaded {successful} tracks, {failed} failed, {skipped} skipped',
        'successful': successful,
        'failed': failed,
        'skipped': skipped,
        'total': len(track_ids),
        'results': results
    }, status=status.HTTP_200_OK)
