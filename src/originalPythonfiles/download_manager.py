import time
import math
from database import get_undownloaded_tracks, count_undownloaded_tracks
from downloader import download_track

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

def download_all_tracks(download_dir, limit=None):
    total_tracks = count_undownloaded_tracks()
    
    if total_tracks == 0:
        print("No tracks to download!")
        return
    
    if limit:
        total_tracks = min(total_tracks, limit)
    
    print(f"Found {total_tracks} tracks to download")
    
    delay = calculate_delay(total_tracks)
    print(f"Using delay of {delay:.2f} seconds between downloads")
    
    tracks = get_undownloaded_tracks(limit=limit)
    
    successful = 0
    failed = 0
    
    for i, (track_id, track_name, album, artist_name) in enumerate(tracks, 1):
        print(f"\n[{i}/{total_tracks}] ", end="")
        
        success = download_track(track_id, track_name, artist_name, album, download_dir)
        
        if success:
            successful += 1
        else:
            failed += 1
        
        if i < total_tracks:
            time.sleep(delay)
    
    print(f"\n\nDownload complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

