#!/usr/bin/env python
"""
Script to re-check all artists in new_tracks table and add missing tracks.

This script:
1. Gets all unique artists from the new_tracks table
2. Fetches complete discography for each artist (now with improved pagination)
3. Adds only missing tracks to the new_tracks table
4. Should now return more than 100 tracks per artist with the fixed pagination
"""

import os
import sys
import django
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import NewTrack
from artistFetcher.views import fetch_artist_discography_helper


def get_unique_artists_from_new_tracks():
    """
    Get all unique artist names from the new_tracks table.
    
    Returns:
        set: Set of unique artist names
    """
    artists = NewTrack.objects.filter(
        artist_name__isnull=False
    ).exclude(
        artist_name=''
    ).values_list('artist_name', flat=True).distinct()
    
    return set(artists)


def update_artist_tracks(artist_name):
    """
    Fetch discography for an artist and add missing tracks to new_tracks table.
    
    Args:
        artist_name (str): Name of the artist
        
    Returns:
        dict: Statistics about the operation
    """
    print(f"\nProcessing: {artist_name}")
    
    try:
        result = fetch_artist_discography_helper(artist_name)
        tracks_data = result.get('tracks', [])
        api_used = result.get('api_used', 'Unknown')
        
        if not tracks_data:
            print(f"  ✗ No tracks found for {artist_name}")
            return {
                'artist': artist_name,
                'tracks_found': 0,
                'new_tracks': 0,
                'duplicates': 0,
                'success': False,
                'api_used': api_used
            }
        
        existing_tracks = set(
            NewTrack.objects.filter(artist_name=artist_name)
            .values_list('track_name', flat=True)
        )
        
        new_count = 0
        duplicate_count = 0
        
        for track_data in tracks_data:
            track_name = track_data.get('track_name', '').strip()
            album = track_data.get('album', '').strip() if track_data.get('album') else ''
            fetched_artist = track_data.get('artist_name', artist_name).strip()
            genre = track_data.get('genre', '').strip() if track_data.get('genre') else ''
            
            if not track_name:
                continue
            
            if track_name not in existing_tracks:
                NewTrack.objects.create(
                    artist_name=fetched_artist,
                    track_name=track_name,
                    album=album if album else None,
                    genre=genre if genre else None
                )
                existing_tracks.add(track_name)
                new_count += 1
            else:
                duplicate_count += 1
        
        print(f"  ✓ Found {len(tracks_data)} tracks (API: {api_used})")
        print(f"    - {new_count} new tracks added")
        if duplicate_count > 0:
            print(f"    - {duplicate_count} duplicates skipped")
        
        if len(tracks_data) > 100:
            print(f"    ⭐ Great! Found more than 100 tracks (pagination working!)")
        
        return {
            'artist': artist_name,
            'tracks_found': len(tracks_data),
            'new_tracks': new_count,
            'duplicates': duplicate_count,
            'success': True,
            'api_used': api_used
        }
    
    except Exception as e:
        print(f"  ✗ Error processing {artist_name}: {e}")
        return {
            'artist': artist_name,
            'tracks_found': 0,
            'new_tracks': 0,
            'duplicates': 0,
            'success': False,
            'error': str(e)
        }


def main():
    """
    Main function to update all artists in new_tracks table.
    """
    print("=" * 60)
    print("Updating New Tracks - Re-checking All Artists")
    print("=" * 60)
    
    print("\nStep 1: Getting unique artists from new_tracks table...")
    unique_artists = get_unique_artists_from_new_tracks()
    
    if not unique_artists:
        print("No artists found in new_tracks table!")
        return
    
    print(f"Found {len(unique_artists)} unique artists:")
    for artist in sorted(list(unique_artists)[:20]):
        print(f"  - {artist}")
    if len(unique_artists) > 20:
        print(f"  ... and {len(unique_artists) - 20} more")
    
    print(f"\nStep 2: Re-fetching discographies for {len(unique_artists)} artists...")
    print("This may take a while depending on the number of artists...")
    print("With improved pagination, you should see more than 100 tracks per artist!\n")
    
    stats = {
        'total_artists': len(unique_artists),
        'artists_processed': 0,
        'artists_failed': 0,
        'total_tracks_found': 0,
        'total_new_tracks': 0,
        'total_duplicates': 0,
        'artists_with_100_plus': 0,
        'youtube_count': 0
    }
    
    for i, artist_name in enumerate(sorted(unique_artists), 1):
        result = update_artist_tracks(artist_name)
        
        stats['total_tracks_found'] += result['tracks_found']
        stats['total_new_tracks'] += result['new_tracks']
        stats['total_duplicates'] += result['duplicates']
        
        if result['tracks_found'] > 100:
            stats['artists_with_100_plus'] += 1
        
        if result.get('api_used') == 'YouTube Music':
            stats['youtube_count'] += 1
        
        if result['success']:
            stats['artists_processed'] += 1
        else:
            stats['artists_failed'] += 1
        
        if i < len(unique_artists):
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total artists processed: {stats['total_artists']}")
    print(f"  Successfully processed: {stats['artists_processed']}")
    print(f"  Failed: {stats['artists_failed']}")
    print(f"  Total tracks found: {stats['total_tracks_found']}")
    print(f"  New tracks added: {stats['total_new_tracks']}")
    print(f"  Duplicates skipped: {stats['total_duplicates']}")
    print(f"  Artists with 100+ tracks: {stats['artists_with_100_plus']}")
    print(f"\nAPI Usage:")
    print(f"  YouTube Music: {stats['youtube_count']} artists")
    print("\nAll missing tracks have been added to the new_tracks table.")


if __name__ == '__main__':
    main()

