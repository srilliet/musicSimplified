import time
from database import get_all_artists, add_new_track, new_track_exists
from artist_fetcher import fetch_artist_discography

def load_all_discographies():
    import os
    
    artists = get_all_artists()
    
    if not artists:
        print("No artists found in database!")
        return
    
    print(f"Found {len(artists)} artists to process")
    
    spotify_configured = bool(os.getenv('SPOTIFY_CLIENT_ID') and os.getenv('SPOTIFY_CLIENT_SECRET'))
    if spotify_configured:
        print("Using Spotify API (primary)")
    else:
        print("Spotify API not configured - using YouTube Music API (fallback)")
        print("For better results, set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables")
    
    print("Fetching discographies from internet...\n")
    
    total_new_tracks = 0
    artists_processed = 0
    artists_failed = 0
    
    for i, artist_name in enumerate(artists, 1):
        print(f"[{i}/{len(artists)}] Processing: {artist_name}")
        
        try:
            tracks = fetch_artist_discography(artist_name)
            
            if not tracks:
                print(f"  ✗ No tracks found for {artist_name}")
                artists_failed += 1
                continue
            
            new_count = 0
            duplicate_count = 0
            
            for track_name, album, artist in tracks:
                if not new_track_exists(artist, track_name):
                    add_new_track(artist, track_name, album)
                    new_count += 1
                else:
                    duplicate_count += 1
            
            total_new_tracks += new_count
            artists_processed += 1
            
            print(f"  ✓ Found {len(tracks)} tracks")
            print(f"    - {new_count} new tracks added")
            if duplicate_count > 0:
                print(f"    - {duplicate_count} duplicates skipped")
            
            if i < len(artists):
                time.sleep(1)
        
        except Exception as e:
            print(f"  ✗ Error processing {artist_name}: {e}")
            artists_failed += 1
            continue
    
    print(f"\n\nProcessing complete!")
    print(f"Artists processed: {artists_processed}")
    print(f"Artists failed: {artists_failed}")
    print(f"Total new tracks discovered: {total_new_tracks}")

