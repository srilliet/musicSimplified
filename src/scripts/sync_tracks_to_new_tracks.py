#!/usr/bin/env python
"""
Script to sync tracks from tracks table to new_tracks table.

For tracks that exist in both tables (matching track_name and artist_name),
updates new_tracks to set downloaded=True and success=True.
"""

import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track, NewTrack  # type: ignore


def safe_print(*args, **kwargs):
    """
    Safe print function that handles Unicode encoding errors.
    """
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: print repr of problematic strings
        cleaned_args = []
        for arg in args:
            if isinstance(arg, str):
                try:
                    cleaned_args.append(repr(arg))
                except:
                    cleaned_args.append(str(arg))
            else:
                cleaned_args.append(arg)
        print(*cleaned_args, **kwargs)


def sync_tracks_to_new_tracks():
    """
    Sync tracks from tracks table to new_tracks table.
    
    For each track in tracks table, find matching new_track by track_name and artist_name.
    If found, update new_track to set downloaded=True and success=True.
    
    Returns:
        dict: Statistics about the sync operation
    """
    safe_print("=" * 60)
    safe_print("Syncing Tracks to New Tracks")
    safe_print("=" * 60)
    
    # Get all tracks from tracks table
    tracks = Track.objects.all()
    
    if not tracks.exists():
        safe_print("\nNo tracks found in tracks table")
        return {
            'total_tracks': 0,
            'matched': 0,
            'updated': 0,
            'already_updated': 0
        }
    
    total_tracks = tracks.count()
    safe_print(f"\nFound {total_tracks} tracks in tracks table")
    safe_print("Searching for matches in new_tracks table...\n")
    
    stats = {
        'total_tracks': total_tracks,
        'matched': 0,
        'updated': 0,
        'already_updated': 0
    }
    
    # Process each track
    for i, track in enumerate(tracks, 1):
        if i % 100 == 0:
            safe_print(f"  Processed {i}/{total_tracks} tracks...")
        
        # Skip if track doesn't have required fields
        if not track.track_name or not track.artist_name:
            continue
        
        # Find matching new_track (case-insensitive match)
        new_tracks = NewTrack.objects.filter(
            track_name__iexact=track.track_name,
            artist_name__iexact=track.artist_name
        )
        
        if new_tracks.exists():
            stats['matched'] += 1
            
            # Update all matching new_tracks (in case there are duplicates)
            for new_track in new_tracks:
                updated = False
                
                # Check if already marked as downloaded and successful
                if new_track.downloaded and new_track.success:
                    stats['already_updated'] += 1
                    continue
                
                # Update if needed
                if not new_track.downloaded:
                    new_track.downloaded = True
                    updated = True
                
                if not new_track.success:
                    new_track.success = True
                    updated = True
                
                if updated:
                    new_track.save()
                    stats['updated'] += 1
                    safe_print(f"[{i}/{total_tracks}] Updated: {track.artist_name} - {track.track_name}")
    
    return stats


def main():
    """
    Main function to sync tracks to new_tracks.
    """
    stats = sync_tracks_to_new_tracks()
    
    safe_print("\n" + "=" * 60)
    safe_print("Sync Complete!")
    safe_print("=" * 60)
    safe_print(f"\nSummary:")
    safe_print(f"  Total tracks checked: {stats['total_tracks']}")
    safe_print(f"  Matches found: {stats['matched']}")
    safe_print(f"  New tracks updated: {stats['updated']}")
    safe_print(f"  Already up to date: {stats['already_updated']}")
    safe_print(f"\nnew_tracks table has been updated with download status.")


if __name__ == '__main__':
    main()

