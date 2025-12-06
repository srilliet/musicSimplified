#!/usr/bin/env python
"""
Script to process artist collaborations in the database.

This script:
1. Finds all tracks where artist_name contains ';' (collaborations)
2. Extracts unique artist names from these collaborations
3. Fetches discography for each artist
4. Saves tracks to the new_tracks table for future downloads
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
from artistFetcher.views import fetch_artist_discography_helper


def extract_artists_from_collaborations():
    """
    Extract unique artist names from tracks that contain collaborations (separated by ';').
    
    Returns:
        set: Set of unique artist names
    """
    collaboration_tracks = Track.objects.filter(artist_name__contains=';')
    
    unique_artists = set()
    
    for track in collaboration_tracks:
        if track.artist_name:
            artists = [artist.strip() for artist in track.artist_name.split(';')]
            unique_artists.update(artists)
    
    return unique_artists


def fetch_and_save_artist_tracks(artist_name):
    """
    Fetch discography for an artist and save to new_tracks table.
    
    Args:
        artist_name (str): Name of the artist
        
    Returns:
        dict: Statistics about the operation
    """
    print(f"\nProcessing: {artist_name}")
    
    try:
        result = fetch_artist_discography_helper(artist_name)
        tracks_data = result.get('tracks', [])
        
        if not tracks_data:
            print(f"  ✗ No tracks found for {artist_name}")
            return {
                'artist': artist_name,
                'tracks_found': 0,
                'new_tracks': 0,
                'duplicates': 0,
                'success': False
            }
        
        new_count = 0
        duplicate_count = 0
        
        for track_data in tracks_data:
            track_name = track_data.get('track_name', '').strip()
            album = track_data.get('album', '').strip() if track_data.get('album') else ''
            fetched_artist = track_data.get('artist_name', artist_name).strip()
            genre = track_data.get('genre', '').strip() if track_data.get('genre') else ''
            
            if not track_name:
                continue
            
            if not NewTrack.objects.filter(
                artist_name=fetched_artist,
                track_name=track_name
            ).exists():
                NewTrack.objects.create(
                    artist_name=fetched_artist,
                    track_name=track_name,
                    album=album if album else None,
                    genre=genre if genre else None
                )
                new_count += 1
            else:
                duplicate_count += 1
        
        print(f"  ✓ Found {len(tracks_data)} tracks")
        print(f"    - {new_count} new tracks added")
        if duplicate_count > 0:
            print(f"    - {duplicate_count} duplicates skipped")
        
        return {
            'artist': artist_name,
            'tracks_found': len(tracks_data),
            'new_tracks': new_count,
            'duplicates': duplicate_count,
            'success': True
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
    Main function to process all collaborations.
    """
    print("=" * 60)
    print("Processing Artist Collaborations")
    print("=" * 60)
    
    print("\nStep 1: Extracting unique artists from collaborations...")
    unique_artists = extract_artists_from_collaborations()
    
    if not unique_artists:
        print("No collaborations found in the database!")
        return
    
    print(f"Found {len(unique_artists)} unique artists from collaborations:")
    for artist in sorted(unique_artists):
        print(f"  - {artist}")
    
    print(f"\nStep 2: Fetching discographies for {len(unique_artists)} artists...")
    print("This may take a while depending on the number of artists...\n")
    
    stats = {
        'total_artists': len(unique_artists),
        'artists_processed': 0,
        'artists_failed': 0,
        'total_tracks_found': 0,
        'total_new_tracks': 0,
        'total_duplicates': 0
    }
    
    for i, artist_name in enumerate(sorted(unique_artists), 1):
        result = fetch_and_save_artist_tracks(artist_name)
        
        stats['total_tracks_found'] += result['tracks_found']
        stats['total_new_tracks'] += result['new_tracks']
        stats['total_duplicates'] += result['duplicates']
        
        if result['success']:
            stats['artists_processed'] += 1
        else:
            stats['artists_failed'] += 1
        
        if i < len(unique_artists):
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total artists processed: {stats['total_artists']}")
    print(f"  Successfully processed: {stats['artists_processed']}")
    print(f"  Failed: {stats['artists_failed']}")
    print(f"  Total tracks found: {stats['total_tracks_found']}")
    print(f"  New tracks added: {stats['total_new_tracks']}")
    print(f"  Duplicates skipped: {stats['total_duplicates']}")
    print("\nAll tracks have been saved to the new_tracks table.")


if __name__ == '__main__':
    main()

