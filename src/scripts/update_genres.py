#!/usr/bin/env python
"""
Script to update genre information for tracks in both tracks and new_tracks tables.

This script:
1. Finds all tracks without genre in both tables
2. Fetches song-level genre from MusicBrainz API for each track
3. Updates each track with its specific genre information
4. Uses rate limiting (2 seconds between requests) to respect MusicBrainz API limits
"""

import os
import sys
import django
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track, NewTrack  # type: ignore
from ytmusicapi import YTMusic
import musicbrainzngs


def get_song_genre_musicbrainz(artist_name, track_name):
    """
    Fetch genre for a specific song from MusicBrainz API.
    Uses 2 second delay to respect rate limits and avoid getting banned.
    
    Args:
        artist_name (str): Name of the artist
        track_name (str): Name of the track
        
    Returns:
        str: Primary genre or None if not found
    """
    try:
        musicbrainzngs.set_useragent("MusicSimplify", "1.0", "https://github.com/srilliet/musicSimplified")
        
        # Search for recordings (songs) by artist and track name
        query = f'artist:"{artist_name}" AND recording:"{track_name}"'
        result = musicbrainzngs.search_recordings(query=query, limit=1)
        time.sleep(2)  # Rate limit: 2 seconds between API calls
        
        if not result.get('recording-list'):
            return None
        
        recording = result['recording-list'][0]
        recording_id = recording.get('id')
        
        if not recording_id:
            return None
        
        # Get detailed recording info with tags
        time.sleep(2)  # Rate limit: 2 seconds between API calls
        try:
            recording_info = musicbrainzngs.get_recording_by_id(recording_id, includes=['tags'])
            
            if 'tag-list' in recording_info.get('recording', {}):
                tags = recording_info['recording']['tag-list']
                if isinstance(tags, list) and len(tags) > 0:
                    if isinstance(tags[0], dict):
                        genre_tags = [tag.get('name', '') for tag in tags if tag.get('name')]
                    else:
                        genre_tags = [tags[0].get('name', '')] if isinstance(tags[0], dict) else []
                    if genre_tags:
                        return genre_tags[0]
        except:
            pass
        
        # Try release-group tags if recording tags not available
        if 'release-list' in recording and len(recording['release-list']) > 0:
            release = recording['release-list'][0]
            release_group_id = release.get('release-group', {}).get('id')
            
            if release_group_id:
                time.sleep(2)  # Rate limit: 2 seconds between API calls
                try:
                    release_group_info = musicbrainzngs.get_release_group_by_id(release_group_id, includes=['tags'])
                    
                    if 'tag-list' in release_group_info.get('release-group', {}):
                        tags = release_group_info['release-group']['tag-list']
                        if isinstance(tags, list) and len(tags) > 0:
                            if isinstance(tags[0], dict):
                                genre_tags = [tag.get('name', '') for tag in tags if tag.get('name')]
                            else:
                                genre_tags = [tags[0].get('name', '')] if isinstance(tags[0], dict) else []
                            if genre_tags:
                                return genre_tags[0]
                except:
                    pass
        
        return None
    except Exception as e:
        return None


def get_artist_genre_youtube_music(artist_name):
    """
    Try to fetch genre for an artist from YouTube Music.
    Note: YouTube Music doesn't directly provide genre, but we can try to infer
    from track categories or use a search-based approach.
    
    Args:
        artist_name (str): Name of the artist
        
    Returns:
        str: Genre or None if not found
    """
    try:
        ytmusic = YTMusic()
        
        search_results = ytmusic.search(query=artist_name, filter='artists', limit=1)
        
        if not search_results:
            return None
        
        artist_id = search_results[0].get('browseId')
        if not artist_id:
            return None
        
        try:
            search_tracks = ytmusic.search(query=f"{artist_name}", filter='songs', limit=5)
            
            if search_tracks:
                for track in search_tracks:
                    video_id = track.get('videoId')
                    if video_id:
                        try:
                            song_info = ytmusic.get_song(video_id)
                            category = song_info.get('category')
                            if category:
                                return category
                        except:
                            continue
        except:
            pass
        
        return None
    except Exception as e:
        return None


def get_song_genre(artist_name, track_name):
    """
    Fetch genre for a specific song, trying MusicBrainz first, then YouTube Music.
    
    Args:
        artist_name (str): Name of the artist
        track_name (str): Name of the track
        
    Returns:
        str: Primary genre or None if not found
    """
    genre = get_song_genre_musicbrainz(artist_name, track_name)
    if genre:
        return genre
    
    # Fallback to YouTube Music (less reliable for song-level)
    genre = get_artist_genre_youtube_music(artist_name)
    return genre


def get_tracks_without_genre():
    """
    Get all tracks without genre from both tables.
    
    Returns:
        list: List of track dictionaries with id, artist_name, track_name, table_type
    """
    tracks_list = []
    
    tracks = Track.objects.filter(
        genre__isnull=True
    ).exclude(
        artist_name__isnull=True
    ).exclude(
        artist_name=''
    ).exclude(
        track_name__isnull=True
    ).exclude(
        track_name=''
    ).values('id', 'artist_name', 'track_name')
    
    for track in tracks:
        tracks_list.append({
            'id': track['id'],
            'artist_name': track['artist_name'],
            'track_name': track['track_name'],
            'table_type': 'tracks'
        })
    
    new_tracks = NewTrack.objects.filter(
        genre__isnull=True
    ).exclude(
        artist_name__isnull=True
    ).exclude(
        artist_name=''
    ).exclude(
        track_name__isnull=True
    ).exclude(
        track_name=''
    ).values('id', 'artist_name', 'track_name')
    
    for track in new_tracks:
        tracks_list.append({
            'id': track['id'],
            'artist_name': track['artist_name'],
            'track_name': track['track_name'],
            'table_type': 'new_tracks'
        })
    
    return tracks_list


def update_track_genre(track_id, artist_name, track_name, table_type, genre):
    """
    Update genre for a specific track.
    
    Args:
        track_id: ID of the track
        artist_name (str): Name of the artist
        track_name (str): Name of the track
        table_type (str): 'tracks' or 'new_tracks'
        genre (str): Genre to set (if None, will fetch from API)
        
    Returns:
        dict: Statistics about the update
    """
    if not genre:
        genre = get_song_genre(artist_name, track_name)
        time.sleep(2)  # Rate limit: 2 seconds after API call
    
    if not genre:
        return {
            'track_id': track_id,
            'artist': artist_name,
            'track': track_name,
            'genre': None,
            'updated': False,
            'success': False
        }
    
    if table_type == 'tracks':
        updated = Track.objects.filter(id=track_id, genre__isnull=True).update(genre=genre)
    else:
        updated = NewTrack.objects.filter(id=track_id, genre__isnull=True).update(genre=genre)
    
    return {
        'track_id': track_id,
        'artist': artist_name,
        'track': track_name,
        'genre': genre,
        'updated': updated > 0,
        'success': True
    }


def main():
    """
    Main function to update genres for all tracks.
    """
    print("=" * 60)
    print("Updating Genre Information")
    print("=" * 60)
    
    print("\n✓ Using MusicBrainz API to fetch genre information")
    
    print("\nStep 1: Finding tracks without genre...")
    tracks_list = get_tracks_without_genre()
    
    if not tracks_list:
        print("No tracks found without genre!")
        return
    
    tracks_count = sum(1 for t in tracks_list if t['table_type'] == 'tracks')
    new_tracks_count = sum(1 for t in tracks_list if t['table_type'] == 'new_tracks')
    
    print(f"Found {len(tracks_list)} tracks with missing genre")
    print(f"  - {tracks_count} tracks in tracks table")
    print(f"  - {new_tracks_count} tracks in new_tracks table")
    print(f"  - Total: {len(tracks_list)} tracks to update")
    
    print(f"\nStep 2: Fetching song-level genres from MusicBrainz...")
    print("⚠️  Rate limiting: 2 seconds between requests to respect MusicBrainz API limits")
    print("This may take a while...\n")
    
    stats = {
        'total_tracks': len(tracks_list),
        'tracks_updated': 0,
        'tracks_failed': 0,
        'tracks_table_updated': 0,
        'new_tracks_table_updated': 0
    }
    
    for i, track_data in enumerate(tracks_list, 1):
        track_id = track_data['id']
        artist_name = track_data['artist_name']
        track_name = track_data['track_name']
        table_type = track_data['table_type']
        
        print(f"[{i}/{len(tracks_list)}] Processing: {artist_name} - {track_name}")
        
        result = update_track_genre(track_id, artist_name, track_name, table_type, None)
        
        if result['success'] and result['updated']:
            stats['tracks_updated'] += 1
            if table_type == 'tracks':
                stats['tracks_table_updated'] += 1
            else:
                stats['new_tracks_table_updated'] += 1
            
            print(f"  ✓ Genre: {result['genre']}")
        else:
            stats['tracks_failed'] += 1
            print(f"  ✗ No genre found")
        
        # Rate limiting: 2 second delay between tracks to be safe
        if i < len(tracks_list):
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total tracks processed: {stats['total_tracks']}")
    print(f"  Successfully updated: {stats['tracks_updated']}")
    print(f"  Failed: {stats['tracks_failed']}")
    print(f"  Tracks table updated: {stats['tracks_table_updated']}")
    print(f"  New tracks table updated: {stats['new_tracks_table_updated']}")
    print(f"  Total tracks updated: {stats['tracks_updated']}")
    print("\nAll genre information has been updated in the database.")


if __name__ == '__main__':
    main()

