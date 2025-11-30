import os
import subprocess
import re
from pathlib import Path

def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    return filename

def download_with_ytdlp(track_name, artist_name, album, download_dir):
    try:
        search_query = f"{artist_name} {track_name}"
        sanitized_artist = sanitize_filename(artist_name) if artist_name else "Unknown Artist"
        sanitized_album = sanitize_filename(album) if album else "Unknown Album"
        sanitized_track = sanitize_filename(track_name)
        
        output_dir = Path(download_dir) / sanitized_artist / sanitized_album
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_dir / f"{sanitized_track}.%(ext)s")
        
        ytdlp_cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '0',
            '--default-search', 'ytsearch',
            '--output', output_template,
            '--no-playlist',
            '--quiet',
            '--no-warnings',
            f'ytsearch1:{search_query}'
        ]
        
        result = subprocess.run(
            ytdlp_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            mp3_file = output_dir / f"{sanitized_track}.mp3"
            if mp3_file.exists():
                return str(mp3_file)
        
        return None
    except Exception as e:
        return None

def download_with_spotdl(track_name, artist_name, album, download_dir):
    original_cwd = os.getcwd()
    try:
        search_query = f"{artist_name} {track_name}"
        sanitized_artist = sanitize_filename(artist_name) if artist_name else "Unknown Artist"
        sanitized_album = sanitize_filename(album) if album else "Unknown Album"
        
        output_dir = Path(download_dir) / sanitized_artist / sanitized_album
        output_dir.mkdir(parents=True, exist_ok=True)
        
        os.chdir(str(output_dir))
        
        spotdl_cmd = [
            'spotdl',
            'download',
            search_query,
            '--format', 'mp3',
            '--output', '{artist} - {title}.{ext}'
        ]
        
        result = subprocess.run(
            spotdl_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            for file in output_dir.glob("*.mp3"):
                return str(file)
        
        return None
    except Exception as e:
        return None
    finally:
        os.chdir(original_cwd)

def download_track(track_id, track_name, artist_name, album, download_dir):
    try:
        from api.models import Track
        track = Track.objects.get(id=track_id)
    except:
        track = None
    
    print(f"Downloading: {artist_name} - {track_name}")
    
    file_path = download_with_ytdlp(track_name, artist_name, album, download_dir)
    
    if file_path:
        print(f"  ✓ Success with yt-dlp: {file_path}")
        if track:
            track.download = 1
            track.failed_download = 0
            track.save()
        return True
    
    print(f"  ✗ yt-dlp failed, trying spotdl...")
    file_path = download_with_spotdl(track_name, artist_name, album, download_dir)
    
    if file_path:
        print(f"  ✓ Success with spotdl: {file_path}")
        if track:
            track.download = 1
            track.failed_download = 0
            track.save()
        return True
    
    print(f"  ✗ Both methods failed")
    if track:
        track.failed_download = 1
        track.save()
    return False

