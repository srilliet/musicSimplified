import os
import time
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)


def fetch_artist_discography_youtube_music(artist_name):
    try:
        logger.info(f"Using YouTube Music API for artist: {artist_name}")
        ytmusic = YTMusic()
        
        search_results = ytmusic.search(query=artist_name, filter='artists', limit=1)
        
        if not search_results:
            logger.warning(f"No artist found on YouTube Music for: {artist_name}")
            return []
        
        artist_id = search_results[0].get('browseId')
        if not artist_id:
            logger.warning(f"No browseId found for artist: {artist_name}")
            return []
        
        tracks = []
        seen_tracks = set()
        
        try:
            artist_albums = ytmusic.get_artist_albums(browseId=artist_id, limit=100)
            total_albums_processed = 0
            
            if artist_albums:
                for album in artist_albums:
                    album_name = album.get('title', '')
                    album_id = album.get('browseId')
                    
                    if album_id:
                        try:
                            album_tracks = ytmusic.get_album(browseId=album_id)
                            for track in album_tracks.get('tracks', []):
                                track_name = track.get('title', '').strip()
                                if track_name:
                                    track_key = (track_name.lower(), artist_name.lower())
                                    if track_key not in seen_tracks:
                                        seen_tracks.add(track_key)
                                        tracks.append({
                                            'track_name': track_name,
                                            'album': album_name,
                                            'artist_name': artist_name,
                                            'genre': None
                                        })
                            time.sleep(0.3)
                            total_albums_processed += 1
                        except Exception as e:
                            logger.debug(f"Error fetching album {album_name}: {e}")
                            continue
            
            logger.info(f"YouTube Music: Found {len(tracks)} tracks from {total_albums_processed} albums for {artist_name}")
        
        except Exception as e:
            logger.warning(f"Error fetching albums from YouTube Music: {e}")
        
        if not tracks or len(tracks) < 50:
            logger.info(f"Searching additional songs for: {artist_name}")
            try:
                search_tracks = ytmusic.search(
                    query=f"{artist_name}",
                    filter='songs',
                    limit=100
                )
                
                if search_tracks:
                    for track in search_tracks:
                        track_name = track.get('title', '').strip()
                        album_name = track.get('album', {}).get('name', '') if track.get('album') else ''
                        if track_name:
                            track_key = (track_name.lower(), artist_name.lower())
                            if track_key not in seen_tracks:
                                seen_tracks.add(track_key)
                                tracks.append({
                                    'track_name': track_name,
                                    'album': album_name,
                                    'artist_name': artist_name,
                                    'genre': None
                                })
            except Exception as e:
                logger.warning(f"Error in YouTube Music search: {e}")
        
        logger.info(f"YouTube Music: Total {len(tracks)} unique tracks found for {artist_name}")
        return tracks
    except Exception as e:
        logger.error(f"YouTube Music error for {artist_name}: {e}")
        return []


def fetch_artist_discography_helper(artist_name):
    api_used = None
    
    tracks = []
    try:
        logger.info(f"Fetching from YouTube Music for: {artist_name}")
        tracks = fetch_artist_discography_youtube_music(artist_name)
        if tracks:
            api_used = 'YouTube Music'
            logger.info(f"Successfully fetched {len(tracks)} tracks from YouTube Music for {artist_name}")
    except Exception as e:
        logger.error(f"YouTube Music fetch failed for {artist_name}: {e}")
    
    result = {
        'artist_name': artist_name,
        'tracks': tracks,
        'count': len(tracks),
        'api_used': api_used if api_used else 'None'
    }
    
    if not tracks:
        logger.warning(f"No tracks found for {artist_name} from any source")
    
    return result


@api_view(['GET', 'POST'])
def fetch_artist_discography(request):
    if request.method == 'GET':
        artist_name = request.query_params.get('artist_name')
    else:
        artist_name = request.data.get('artist_name')
    
    if not artist_name:
        return Response(
            {'error': 'artist_name parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = fetch_artist_discography_helper(artist_name)
    return Response(result, status=status.HTTP_200_OK)
