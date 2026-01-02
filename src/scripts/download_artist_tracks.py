#!/usr/bin/env python
"""
Script to download tracks for a specific artist from new_tracks table.

This script:
1. Prompts user for artist name
2. Scans new_tracks table for tracks by that artist
3. Downloads each track using yt-dlp or spotdl
4. Creates proper folder structure: Artist/Album/Song
5. Updates tracks table with downloaded track info
6. Updates new_tracks table with downloaded=True and success=True
"""

import os
import sys
import django
import re
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track, NewTrack, Settings  # type: ignore
from django.conf import settings as django_settings
import subprocess


def safe_unicode_string(text):
    """
    Safely handle Unicode strings, removing invalid surrogates.
    
    Args:
        text: String that may contain invalid Unicode
        
    Returns:
        str: Cleaned Unicode string
    """
    if text is None:
        return None
    
    try:
        text.encode('utf-8', errors='strict')
        return text
    except UnicodeEncodeError:
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    except (AttributeError, TypeError):
        text = str(text)
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')


def safe_print(*args, **kwargs):
    """
    Safe print function that handles Unicode encoding errors.
    """
    try:
        cleaned_args = []
        for arg in args:
            if isinstance(arg, str):
                cleaned_args.append(safe_unicode_string(arg))
            else:
                cleaned_args.append(arg)
        print(*cleaned_args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError):
        cleaned_args = []
        for arg in args:
            if isinstance(arg, str):
                try:
                    cleaned_args.append(safe_unicode_string(arg))
                except:
                    cleaned_args.append(repr(arg))
            else:
                cleaned_args.append(arg)
        print(*cleaned_args, **kwargs)


def sanitize_filename(filename):
    """
    Sanitize a filename to remove invalid characters for filesystem.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized name safe for filesystem
    """
    if not filename:
        return "Unknown"
    
    # Remove or replace invalid filesystem characters
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename).strip()
    
    if not filename:
        return "Unknown"
    
    return filename


def download_with_ytdlp(track_name, artist_name, album, download_dir):
    """
    Download track using yt-dlp.
    
    Args:
        track_name (str): Track name
        artist_name (str): Artist name
        album (str): Album name
        download_dir (str): Base download directory
        
    Returns:
        str: Path to downloaded file or None if failed
    """
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
            f'ytsearch1:{search_query}'
        ]
        
        result = subprocess.run(
            ytdlp_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Check if command succeeded
        if result.returncode != 0:
            safe_print(f"    yt-dlp error: {result.stderr[:200] if result.stderr else 'Unknown error'}")
            return None
        
        # Check for the expected file
        mp3_file = output_dir / f"{sanitized_track}.mp3"
        
        # Also check for any .mp3 file in the directory (in case filename differs)
        if not mp3_file.exists():
            mp3_files = list(output_dir.glob("*.mp3"))
            if mp3_files:
                # Use the first mp3 file found
                mp3_file = mp3_files[0]
                safe_print(f"    Found file with different name: {mp3_file.name}")
            else:
                safe_print(f"    No MP3 file found in {output_dir}")
                safe_print(f"    Files in directory: {list(output_dir.glob('*'))}")
                return None
        
        # Verify file actually exists and has content
        if mp3_file.exists() and mp3_file.stat().st_size > 0:
            return str(mp3_file)
        else:
            safe_print(f"    File exists but is empty or invalid")
            return None
            
    except subprocess.TimeoutExpired:
        safe_print(f"    yt-dlp timed out")
        return None
    except Exception as e:
        safe_print(f"    yt-dlp exception: {str(e)}")
        return None


def download_with_spotdl(track_name, artist_name, album, download_dir):
    """
    Download track using spotdl.
    
    Args:
        track_name (str): Track name
        artist_name (str): Artist name
        album (str): Album name
        download_dir (str): Base download directory
        
    Returns:
        str: Path to downloaded file or None if failed
    """
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
        
        if result.returncode != 0:
            safe_print(f"    spotdl error: {result.stderr[:200] if result.stderr else 'Unknown error'}")
            return None
        
        # Check for downloaded files
        mp3_files = list(output_dir.glob("*.mp3"))
        if mp3_files:
            # Verify file has content
            for file in mp3_files:
                if file.stat().st_size > 0:
                    return str(file)
            safe_print(f"    Files found but all are empty")
            return None
        else:
            safe_print(f"    No MP3 files found in {output_dir}")
            return None
            
    except subprocess.TimeoutExpired:
        safe_print(f"    spotdl timed out")
        return None
    except Exception as e:
        safe_print(f"    spotdl exception: {str(e)}")
        return None
    finally:
        os.chdir(original_cwd)


def download_track(new_track, download_dir, root_music_path):
    """
    Download a track from new_tracks table.
    
    Args:
        new_track (NewTrack): NewTrack instance to download
        download_dir (str): Base download directory
        root_music_path (str): Root music path for relative_path calculation
        
    Returns:
        dict: Result with 'success', 'file_path', 'method', 'error'
    """
    track_name = new_track.track_name
    artist_name = new_track.artist_name
    album = new_track.album
    
    safe_print(f"\nDownloading: {artist_name} - {track_name}")
    if album:
        safe_print(f"  Album: {album}")
    
    # Try yt-dlp first
    file_path = download_with_ytdlp(track_name, artist_name, album, download_dir)
    
    if file_path:
        # Verify file actually exists and has content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            safe_print(f"  ✗ File path reported but file doesn't exist: {file_path}")
            return {
                'success': False,
                'error': 'File not found after download'
            }
        
        file_size = file_path_obj.stat().st_size
        if file_size == 0:
            safe_print(f"  ✗ File exists but is empty (0 bytes)")
            return {
                'success': False,
                'error': 'Downloaded file is empty'
            }
        
        safe_print(f"  ✓ Success with yt-dlp: {file_path} ({file_size} bytes)")
        
        # Calculate relative path from root_music_path
        try:
            relative_path = os.path.relpath(file_path, root_music_path)
            relative_path = safe_unicode_string(relative_path)
        except:
            relative_path = None
        
        return {
            'success': True,
            'file_path': file_path,
            'method': 'yt-dlp',
            'relative_path': relative_path
        }
    
    # Try spotdl as fallback
    safe_print(f"  ✗ yt-dlp failed, trying spotdl...")
    file_path = download_with_spotdl(track_name, artist_name, album, download_dir)
    
    if file_path:
        # Verify file actually exists and has content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            safe_print(f"  ✗ File path reported but file doesn't exist: {file_path}")
            return {
                'success': False,
                'error': 'File not found after download'
            }
        
        file_size = file_path_obj.stat().st_size
        if file_size == 0:
            safe_print(f"  ✗ File exists but is empty (0 bytes)")
            return {
                'success': False,
                'error': 'Downloaded file is empty'
            }
        
        safe_print(f"  ✓ Success with spotdl: {file_path} ({file_size} bytes)")
        
        # Calculate relative path from root_music_path
        try:
            relative_path = os.path.relpath(file_path, root_music_path)
            relative_path = safe_unicode_string(relative_path)
        except:
            relative_path = None
        
        return {
            'success': True,
            'file_path': file_path,
            'method': 'spotdl',
            'relative_path': relative_path
        }
    
    safe_print(f"  ✗ Both methods failed")
    return {
        'success': False,
        'error': 'Download failed with both methods'
    }


def find_or_create_track(new_track, relative_path):
    """
    Find existing track or create new one in tracks table.
    
    Args:
        new_track (NewTrack): NewTrack instance
        relative_path (str): Relative path to the file
        
    Returns:
        Track: Track instance
    """
    # Try to find existing track by relative_path
    if relative_path:
        existing = Track.objects.filter(relative_path=relative_path).first()
        if existing:
            return existing
    
    # Try to find by artist + track name
    existing = Track.objects.filter(
        artist_name__iexact=new_track.artist_name,
        track_name__iexact=new_track.track_name
    ).first()
    
    if existing:
        # Update with relative_path if missing
        if relative_path and not existing.relative_path:
            existing.relative_path = relative_path
            existing.save()
        return existing
    
    # Create new track
    track = Track(
        track_name=safe_unicode_string(new_track.track_name),
        artist_name=safe_unicode_string(new_track.artist_name),
        album=safe_unicode_string(new_track.album) if new_track.album else None,
        genre=safe_unicode_string(new_track.genre) if new_track.genre else None,
        relative_path=safe_unicode_string(relative_path) if relative_path else None
    )
    track.save()
    return track


def download_artist_tracks(artist_name, download_dir=None, root_music_path=None):
    """
    Download all tracks for a specific artist from new_tracks table.
    
    Args:
        artist_name (str): Artist name to download tracks for
        download_dir (str): Base download directory (optional)
        root_music_path (str): Root music path (optional)
        
    Returns:
        dict: Statistics about the download operation
    """
    # Get settings from database
    db_settings = Settings.get_settings()
    
    # Use root_music_path from settings as the download directory
    # This ensures files go to the correct music directory structure
    if not download_dir:
        download_dir = db_settings.root_music_path
        if not download_dir:
            download_dir = getattr(django_settings, 'ROOT_MUSIC_PATH', '/home/stephen/Music')
    
    # root_music_path should be the same as download_dir for relative_path calculation
    if not root_music_path:
        root_music_path = db_settings.root_music_path
        if not root_music_path:
            root_music_path = getattr(django_settings, 'ROOT_MUSIC_PATH', '/home/stephen/Music')
    
    safe_print("=" * 60)
    safe_print(f"Downloading Tracks for: {artist_name}")
    safe_print("=" * 60)
    safe_print(f"\nDownload directory: {download_dir}")
    safe_print(f"Root music path: {root_music_path}")
    
    # Find all tracks for this artist (for statistics)
    all_artist_tracks = NewTrack.objects.filter(artist_name__iexact=artist_name)
    total_artist_tracks = all_artist_tracks.count()
    downloaded_count = all_artist_tracks.filter(downloaded=True).count()
    undownloaded_count = all_artist_tracks.filter(downloaded=False).count()
    
    safe_print(f"\nArtist tracks summary:")
    safe_print(f"  Total tracks for {artist_name}: {total_artist_tracks}")
    safe_print(f"  Already downloaded: {downloaded_count}")
    safe_print(f"  To download: {undownloaded_count}")
    
    # Find tracks in new_tracks table that haven't been downloaded yet
    tracks = NewTrack.objects.filter(
        artist_name__iexact=artist_name,
        downloaded=False  # Only download tracks that haven't been downloaded yet
    )
    
    if not tracks.exists():
        safe_print(f"\nNo undownloaded tracks found for artist: {artist_name}")
        safe_print(f"All tracks for this artist are already marked as downloaded.")
        return {
            'total_tracks': 0,
            'successful': 0,
            'failed': 0,
            'skipped': downloaded_count
        }
    
    total_tracks = tracks.count()
    safe_print(f"\nFound {total_tracks} tracks to download")
    safe_print("\nStarting downloads...\n")
    
    stats = {
        'total_tracks': total_tracks,
        'successful': 0,
        'failed': 0,
        'skipped': downloaded_count
    }
    
    # Download each track
    for i, new_track in enumerate(tracks, 1):
        safe_print(f"[{i}/{total_tracks}] Processing: {new_track.track_name}")
        
        # Double-check that this track hasn't been downloaded (safety check)
        new_track.refresh_from_db()
        if new_track.downloaded:
            safe_print(f"  ⚠ Skipping: Already marked as downloaded (may have been updated by another process)")
            stats['skipped'] += 1
            continue
        
        # Mark as downloaded (attempted)
        new_track.downloaded = True
        new_track.save()
        
        # Download the track
        result = download_track(new_track, download_dir, root_music_path)
        
        if result.get('success'):
            # Update new_tracks table
            new_track.success = True
            new_track.save()
            
            # Update or create track in tracks table
            relative_path = result.get('relative_path')
            track = find_or_create_track(new_track, relative_path)
            
            stats['successful'] += 1
            safe_print(f"  ✓ Track added to tracks table (ID: {track.id})")
        else:
            new_track.success = False
            new_track.save()
            stats['failed'] += 1
            error = result.get('error', 'Unknown error')
            safe_print(f"  ✗ Failed: {error}")
        
        # Rate limiting - wait between downloads
        if i < total_tracks:
            time.sleep(2)  # 2 second delay between downloads
    
    return stats


def main():
    """
    Main function to prompt for artist and download tracks.
    """
    safe_print("=" * 60)
    safe_print("Download Artist Tracks")
    safe_print("=" * 60)
    
    # Prompt for artist name
    artist_name = input("\nEnter artist name to download: ").strip()
    
    if not artist_name:
        safe_print("Error: Artist name cannot be empty")
        return
    
    # Confirm
    safe_print(f"\nYou entered: {artist_name}")
    confirm = input("Is this correct? (y/n): ").strip().lower()
    
    if confirm != 'y':
        safe_print("Cancelled.")
        return
    
    # Download tracks
    stats = download_artist_tracks(artist_name)
    
    # Print summary
    safe_print("\n" + "=" * 60)
    safe_print("Download Complete!")
    safe_print("=" * 60)
    safe_print(f"\nSummary:")
    safe_print(f"  Total tracks to download: {stats['total_tracks']}")
    safe_print(f"  Successful: {stats['successful']}")
    safe_print(f"  Failed: {stats['failed']}")
    safe_print(f"  Skipped (already downloaded): {stats.get('skipped', 0)}")
    safe_print(f"\nTracks have been downloaded and added to the tracks table.")
    safe_print(f"new_tracks table has been updated with download status.")


if __name__ == '__main__':
    main()

