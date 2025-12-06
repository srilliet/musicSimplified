#!/usr/bin/env python
"""
Script to update genre information for tracks in both tracks and new_tracks tables.

This script:
1. Finds all tracks without genre in both tables
2. Groups tracks by artist to minimize API calls
3. Fetches genre from Spotify API for each artist
4. Updates all tracks for that artist with the genre information
"""

import os
import sys
import django
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track, NewTrack
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from ytmusicapi import YTMusic


def get_spotify_client():
    """Get Spotify client if credentials are available."""
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        return sp
    except Exception as e:
        print(f"Error creating Spotify client: {e}")
        return None


def get_artist_genre_spotify(artist_name, spotify_client):
    """
    Fetch genre for an artist from Spotify.
    
    Args:
        artist_name (str): Name of the artist
        spotify_client: Spotify client instance
        
    Returns:
        str: Primary genre or None if not found
    """
    try:
        results = spotify_client.search(q=f'artist:{artist_name}', type='artist', limit=1)
        
        if not results['artists']['items']:
            return None
        
        artist = results['artists']['items'][0]
        genres = artist.get('genres', [])
        
        if genres:
            return genres[0]
        
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


def get_artist_genre(artist_name, spotify_client=None):
    """
    Fetch genre for an artist, trying Spotify first, then YouTube Music.
    
    Args:
        artist_name (str): Name of the artist
        spotify_client: Spotify client instance (optional)
        
    Returns:
        str: Primary genre or None if not found
    """
    genre = None
    
    if spotify_client:
        genre = get_artist_genre_spotify(artist_name, spotify_client)
        if genre:
            return genre
    
    genre = get_artist_genre_youtube_music(artist_name)
    return genre


def get_tracks_without_genre():
    """
    Get all tracks without genre from both tables, grouped by artist.
    
    Returns:
        dict: {artist_name: {'tracks': [track_ids], 'new_tracks': [new_track_ids]}}
    """
    tracks_by_artist = {}
    
    tracks = Track.objects.filter(
        genre__isnull=True
    ).exclude(
        artist_name__isnull=True
    ).exclude(
        artist_name=''
    ).values('id', 'artist_name')
    
    for track in tracks:
        artist = track['artist_name']
        if artist not in tracks_by_artist:
            tracks_by_artist[artist] = {'tracks': [], 'new_tracks': []}
        tracks_by_artist[artist]['tracks'].append(track['id'])
    
    new_tracks = NewTrack.objects.filter(
        genre__isnull=True
    ).exclude(
        artist_name__isnull=True
    ).exclude(
        artist_name=''
    ).values('id', 'artist_name')
    
    for track in new_tracks:
        artist = track['artist_name']
        if artist not in tracks_by_artist:
            tracks_by_artist[artist] = {'tracks': [], 'new_tracks': []}
        tracks_by_artist[artist]['new_tracks'].append(track['id'])
    
    return tracks_by_artist


def update_artist_genre(artist_name, genre, spotify_client):
    """
    Update genre for all tracks of a specific artist.
    
    Args:
        artist_name (str): Name of the artist
        genre (str): Genre to set
        spotify_client: Spotify client instance
        
    Returns:
        dict: Statistics about the update
    """
    if not genre:
        genre = get_artist_genre(artist_name, spotify_client)
    
    if not genre:
        return {
            'artist': artist_name,
            'genre': None,
            'tracks_updated': 0,
            'new_tracks_updated': 0,
            'success': False
        }
    
    tracks_updated = Track.objects.filter(
        artist_name=artist_name,
        genre__isnull=True
    ).update(genre=genre)
    
    new_tracks_updated = NewTrack.objects.filter(
        artist_name=artist_name,
        genre__isnull=True
    ).update(genre=genre)
    
    return {
        'artist': artist_name,
        'genre': genre,
        'tracks_updated': tracks_updated,
        'new_tracks_updated': new_tracks_updated,
        'success': True
    }


def main():
    """
    Main function to update genres for all tracks.
    """
    print("=" * 60)
    print("Updating Genre Information")
    print("=" * 60)
    
    spotify_client = get_spotify_client()
    
    if spotify_client:
        print("\n✓ Spotify API configured - will use Spotify first, YouTube Music as fallback")
    else:
        print("\n⚠️  Spotify API credentials not configured!")
        print("Will use YouTube Music API to fetch genre information.")
        print("(Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET for better results)")
    
    print("\nStep 1: Finding tracks without genre...")
    tracks_by_artist = get_tracks_without_genre()
    
    if not tracks_by_artist:
        print("No tracks found without genre!")
        return
    
    total_tracks = sum(len(data['tracks']) for data in tracks_by_artist.values())
    total_new_tracks = sum(len(data['new_tracks']) for data in tracks_by_artist.values())
    
    print(f"Found {len(tracks_by_artist)} unique artists with missing genre")
    print(f"  - {total_tracks} tracks in tracks table")
    print(f"  - {total_new_tracks} tracks in new_tracks table")
    print(f"  - Total: {total_tracks + total_new_tracks} tracks to update")
    
    api_source = "Spotify/YouTube Music" if spotify_client else "YouTube Music"
    print(f"\nStep 2: Fetching genres from {api_source} for {len(tracks_by_artist)} artists...")
    print("This may take a while...\n")
    
    stats = {
        'total_artists': len(tracks_by_artist),
        'artists_processed': 0,
        'artists_failed': 0,
        'total_tracks_updated': 0,
        'total_new_tracks_updated': 0,
        'total_updated': 0
    }
    
    for i, (artist_name, track_data) in enumerate(sorted(tracks_by_artist.items()), 1):
        track_count = len(track_data['tracks'])
        new_track_count = len(track_data['new_tracks'])
        total_count = track_count + new_track_count
        
        print(f"[{i}/{len(tracks_by_artist)}] Processing: {artist_name} ({total_count} tracks)")
        
        genre = get_artist_genre(artist_name, spotify_client)
        result = update_artist_genre(artist_name, genre, spotify_client)
        
        if result['success']:
            stats['artists_processed'] += 1
            stats['total_tracks_updated'] += result['tracks_updated']
            stats['total_new_tracks_updated'] += result['new_tracks_updated']
            stats['total_updated'] += result['tracks_updated'] + result['new_tracks_updated']
            
            print(f"  ✓ Genre: {result['genre']}")
            print(f"    - Updated {result['tracks_updated']} tracks")
            print(f"    - Updated {result['new_tracks_updated']} new_tracks")
        else:
            stats['artists_failed'] += 1
            print(f"  ✗ No genre found")
        
        if i < len(tracks_by_artist):
            time.sleep(0.2)
    
    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total artists processed: {stats['total_artists']}")
    print(f"  Successfully processed: {stats['artists_processed']}")
    print(f"  Failed: {stats['artists_failed']}")
    print(f"  Tracks updated: {stats['total_tracks_updated']}")
    print(f"  New tracks updated: {stats['total_new_tracks_updated']}")
    print(f"  Total tracks updated: {stats['total_updated']}")
    print("\nAll genre information has been updated in the database.")


if __name__ == '__main__':
    main()

