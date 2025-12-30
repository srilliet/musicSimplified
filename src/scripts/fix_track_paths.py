#!/usr/bin/env python
"""
Script to fix relative_path for tracks that were moved.

Updates tracks with IDs 8600-8690 to have correct relative_path
by removing the old path prefix and keeping only the artist/subfolder structure.
"""

import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track  # type: ignore
import re


def fix_track_paths(start_id=8600, end_id=8690):
    """
    Fix relative_path for tracks in the specified ID range.
    
    Args:
        start_id (int): Starting track ID
        end_id (int): Ending track ID
        
    Returns:
        dict: Statistics about the update
    """
    print("=" * 60)
    print("Fixing Track Paths")
    print("=" * 60)
    print(f"\nUpdating tracks with IDs {start_id} to {end_id}")
    
    # Get tracks in the range
    tracks = Track.objects.filter(id__gte=start_id, id__lte=end_id)
    
    if not tracks.exists():
        print(f"No tracks found in range {start_id}-{end_id}")
        return {
            'total': 0,
            'updated': 0,
            'skipped': 0
        }
    
    total = tracks.count()
    print(f"Found {total} tracks to check")
    print("\nProcessing...\n")
    
    stats = {
        'total': total,
        'updated': 0,
        'skipped': 0
    }
    
    for track in tracks:
        old_path = track.relative_path
        print(f"Track ID {track.id}: {track.artist_name} - {track.track_name}")
        print(f"  Old path: {old_path}")
        
        if not old_path:
            print(f"  ⚠ No path to fix, skipping")
            stats['skipped'] += 1
            continue
        
        # Remove the old path prefix: ../../Data/downloads/
        # The path should be: ../../Data/downloads/The Dead South/Good Company/In Hell I'll Be in Good Company.mp3
        # We want: The Dead South/Good Company/In Hell I'll Be in Good Company.mp3
        
        new_path = old_path
        
        # Remove the old path prefix - look for "Data/downloads/" or "downloads/" and keep everything after
        # This handles patterns like: ../../Data/downloads/, ../Data/downloads/, etc.
        if 'Data/downloads/' in new_path:
            # Split on 'Data/downloads/' and take everything after
            parts = new_path.split('Data/downloads/', 1)
            if len(parts) > 1:
                new_path = parts[1]
        elif 'downloads/' in new_path:
            # Split on 'downloads/' and take everything after
            parts = new_path.split('downloads/', 1)
            if len(parts) > 1:
                new_path = parts[1]
        else:
            # Try to remove relative path prefixes (../)
            new_path = re.sub(r'^\.\.?/\.\.?/', '', new_path)
            # Remove any leading slashes
            new_path = new_path.lstrip('/')
        
        # Clean up the path - remove any leading slashes, dots, or spaces
        new_path = new_path.lstrip('/').lstrip('.').strip()
        
        # The path should now be: "The Dead South/Good Company/In Hell I'll Be in Good Company.mp3"
        # Verify it starts with the artist name (case-insensitive check)
        if track.artist_name:
            artist_name = track.artist_name.strip()
            # Check if path already starts with artist name (case-insensitive)
            if not new_path.lower().startswith(artist_name.lower()):
                # Path doesn't start with artist - this shouldn't happen but handle it
                print(f"  ⚠ Warning: Path doesn't start with artist name")
                print(f"     Artist: {artist_name}")
                print(f"     Path: {new_path}")
                # Try to find artist in path
                artist_lower = artist_name.lower()
                path_lower = new_path.lower()
                if artist_lower in path_lower:
                    # Find where artist name starts in path
                    idx = path_lower.find(artist_lower)
                    new_path = new_path[idx:]
                else:
                    # Prepend artist name
                    new_path = f"{artist_name}/{new_path}"
        
        if new_path == old_path:
            print(f"  ✓ Path already correct")
            stats['skipped'] += 1
        else:
            track.relative_path = new_path
            track.save()
            print(f"  ✓ Updated to: {new_path}")
            stats['updated'] += 1
        
        print()
    
    return stats


def main():
    """
    Main function to fix track paths.
    """
    stats = fix_track_paths(start_id=8600, end_id=8690)
    
    print("=" * 60)
    print("Update Complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total tracks checked: {stats['total']}")
    print(f"  Tracks updated: {stats['updated']}")
    print(f"  Tracks skipped: {stats['skipped']}")
    print(f"\nPaths have been updated to use correct relative paths.")


if __name__ == '__main__':
    main()

