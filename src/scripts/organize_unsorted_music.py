#!/usr/bin/env python
"""
Script to organize unsorted music files into proper folder structure.

This script:
1. Reads files from /home/stephen/Music/1 a not sorted
2. For each song file:
   - Reads metadata tags if possible
   - If metadata not available, uses API call to find album and artist
   - Creates folder structure: Artist/Album/
   - Moves song to that folder
   - If folder already exists (same artist and album), just moves the song
"""

import os
import sys
import django
import re
import time
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Settings  # type: ignore
from django.conf import settings as django_settings
import musicbrainzngs
from ytmusicapi import YTMusic
from mutagen import File as MutagenFile  # type: ignore
from mutagen.easyid3 import EasyID3
from mutagen.id3._util import ID3NoHeaderError  # type: ignore


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
        # Try to encode/decode to catch invalid surrogates
        text.encode('utf-8', errors='strict')
        return text
    except UnicodeEncodeError:
        # Remove invalid surrogates
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    except (AttributeError, TypeError):
        # Not a string, convert to string first
        text = str(text)
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')


def safe_print(*args, **kwargs):
    """
    Safe print function that handles Unicode encoding errors.
    
    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments for print
    """
    try:
        # Clean all string arguments
        cleaned_args = []
        for arg in args:
            if isinstance(arg, str):
                cleaned_args.append(safe_unicode_string(arg))
            else:
                cleaned_args.append(arg)
        print(*cleaned_args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: print repr of problematic strings
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


# Supported audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wav', '.wma', '.opus'}


def sanitize_filename(name):
    """
    Sanitize a filename to remove invalid characters for filesystem.
    
    Args:
        name (str): Original name
        
    Returns:
        str: Sanitized name safe for filesystem
    """
    if not name:
        return "Unknown"
    
    # Remove or replace invalid filesystem characters
    # Windows/Linux invalid chars: < > : " / \ | ? *
    invalid_chars = r'[<>:"/\\|?*]'
    name = re.sub(invalid_chars, '', name)
    
    # Remove leading/trailing dots and spaces (Windows issue)
    name = name.strip('. ')
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name).strip()
    
    # If empty after sanitization, return "Unknown"
    if not name:
        return "Unknown"
    
    return name


def read_metadata_tags(file_path):
    """
    Read metadata tags (ID3) from audio file.
    
    Supports MP3, FLAC, M4A, and other formats via mutagen.
    
    Args:
        file_path (str): Full path to audio file
        
    Returns:
        dict: Dictionary with 'artist', 'title', 'album', 'genre' or None if error
    """
    try:
        audio_file = MutagenFile(file_path)
        
        if audio_file is None:
            return None
        
        metadata = {}
        
        # Try to get tags - different formats use different methods
        try:
            # For MP3 files with ID3 tags
            if hasattr(audio_file, 'tags') and audio_file.tags:
                # Try EasyID3 first (simpler)
                try:
                    easy_id3 = EasyID3(file_path)
                    artist_list = easy_id3.get('artist', [None])
                    title_list = easy_id3.get('title', [None])
                    album_list = easy_id3.get('album', [None])
                    genre_list = easy_id3.get('genre', [None])
                    metadata['artist'] = artist_list[0] if artist_list and artist_list[0] else None
                    metadata['title'] = title_list[0] if title_list and title_list[0] else None
                    metadata['album'] = album_list[0] if album_list and album_list[0] else None
                    metadata['genre'] = genre_list[0] if genre_list and genre_list[0] else None
                except (ID3NoHeaderError, AttributeError, KeyError):
                    # Fallback to regular ID3 tags
                    if hasattr(audio_file, 'tags'):
                        tags = audio_file.tags
                        metadata['artist'] = tags.get('TPE1', [None])[0] if 'TPE1' in tags else (tags.get('TPE2', [None])[0] if 'TPE2' in tags else None)
                        metadata['title'] = tags.get('TIT2', [None])[0] if 'TIT2' in tags else None
                        metadata['album'] = tags.get('TALB', [None])[0] if 'TALB' in tags else None
                        metadata['genre'] = tags.get('TCON', [None])[0] if 'TCON' in tags else None
        except:
            pass
        
        # For other formats (FLAC, M4A, etc.) - use common tag names
        if not metadata.get('artist') and hasattr(audio_file, 'tags'):
            tags = audio_file.tags
            # Try common tag names
            for tag_key in ['artist', 'ARTIST', 'TPE1', '©ART']:
                if tag_key in tags:
                    value = tags[tag_key]
                    if isinstance(value, list) and len(value) > 0:
                        metadata['artist'] = value[0]
                    elif isinstance(value, str):
                        metadata['artist'] = value
                    break
            
            for tag_key in ['title', 'TITLE', 'TIT2', '©nam']:
                if tag_key in tags:
                    value = tags[tag_key]
                    if isinstance(value, list) and len(value) > 0:
                        metadata['title'] = value[0]
                    elif isinstance(value, str):
                        metadata['title'] = value
                    break
            
            for tag_key in ['album', 'ALBUM', 'TALB', '©alb']:
                if tag_key in tags:
                    value = tags[tag_key]
                    if isinstance(value, list) and len(value) > 0:
                        metadata['album'] = value[0]
                    elif isinstance(value, str):
                        metadata['album'] = value
                    break
            
            for tag_key in ['genre', 'GENRE', 'TCON', '©gen']:
                if tag_key in tags:
                    value = tags[tag_key]
                    if isinstance(value, list) and len(value) > 0:
                        metadata['genre'] = value[0]
                    elif isinstance(value, str):
                        metadata['genre'] = value
                    break
        
        # Clean Unicode issues in all metadata values
        for key in metadata:
            if metadata[key]:
                metadata[key] = safe_unicode_string(metadata[key])
        
        # Return None if no metadata found
        if not any(metadata.values()):
            return None
        
        return metadata
        
    except Exception as e:
        # Silently fail - file might not have tags or be corrupted
        return None


def extract_track_name_from_filename(filename):
    """
    Extract clean track name from filename.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Clean track name
    """
    # Clean Unicode issues first
    filename = safe_unicode_string(filename)
    
    if not filename:
        return ""
    
    # Remove file extension
    name = os.path.splitext(filename)[0]
    
    # Remove track numbers at the start
    name = re.sub(r'^\d+\s*[-.]?\s*', '', name, flags=re.IGNORECASE)
    
    # Normalize special characters
    name = name.replace('_', ' ')
    
    # Remove multiple spaces and strip
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def search_album_artist_musicbrainz(track_name):
    """
    Search for album and artist information using MusicBrainz API.
    
    Args:
        track_name (str): Name of the track
        
    Returns:
        tuple: (artist_name, album_name) or (None, None) if not found
    """
    try:
        musicbrainzngs.set_useragent("MusicSimplify", "1.0", "https://github.com/srilliet/musicSimplified")
        
        # Search for recordings (songs) by track name
        query = f'recording:"{track_name}"'
        result = musicbrainzngs.search_recordings(query=query, limit=1)
        time.sleep(2)  # Rate limit: 2 seconds between API calls
        
        if not result.get('recording-list'):
            return None, None
        
        recording = result['recording-list'][0]
        
        # Get artist name
        artist_name = None
        if 'artist-credit' in recording:
            artist_credit = recording['artist-credit']
            if isinstance(artist_credit, list) and len(artist_credit) > 0:
                artist = artist_credit[0]
                if isinstance(artist, dict) and 'artist' in artist:
                    artist_name = artist['artist'].get('name')
            elif isinstance(artist_credit, dict) and 'name' in artist_credit:
                artist_name = artist_credit.get('name')
        
        # Get album name from release
        album_name = None
        if 'release-list' in recording and len(recording['release-list']) > 0:
            release = recording['release-list'][0]
            if 'release-group' in release:
                release_group = release['release-group']
                album_name = release_group.get('title')
        
        # If we have artist but no album, try to get it from release
        if artist_name and not album_name:
            if 'release-list' in recording and len(recording['release-list']) > 0:
                release = recording['release-list'][0]
                album_name = release.get('title')
        
        return artist_name, album_name
        
    except Exception as e:
        return None, None


def search_album_artist_youtube_music(track_name):
    """
    Search for album and artist information using YouTube Music API.
    
    Args:
        track_name (str): Name of the track
        
    Returns:
        tuple: (artist_name, album_name) or (None, None) if not found
    """
    try:
        ytmusic = YTMusic()
        
        # Search for the track
        search_results = ytmusic.search(query=track_name, filter='songs', limit=1)
        
        if not search_results:
            return None, None
        
        track_info = search_results[0]
        
        # Get artist name
        artist_name = None
        if 'artists' in track_info:
            artists = track_info['artists']
            if isinstance(artists, list) and len(artists) > 0:
                artist_name = artists[0].get('name')
            elif isinstance(artists, dict):
                artist_name = artists.get('name')
        
        # Get album name
        album_name = None
        if 'album' in track_info:
            album = track_info['album']
            if isinstance(album, dict):
                album_name = album.get('name')
            elif isinstance(album, str):
                album_name = album
        
        return artist_name, album_name
        
    except Exception as e:
        return None, None


def get_album_artist_from_api(track_name):
    """
    Get album and artist information from API (tries MusicBrainz first, then YouTube Music).
    
    Args:
        track_name (str): Name of the track
        
    Returns:
        tuple: (artist_name, album_name) or (None, None) if not found
    """
    if not track_name:
        return None, None
    
    # Try MusicBrainz first
    artist_name, album_name = search_album_artist_musicbrainz(track_name)
    if artist_name:
        return artist_name, album_name
    
    # Fallback to YouTube Music
    artist_name, album_name = search_album_artist_youtube_music(track_name)
    return artist_name, album_name


def organize_music_files(source_dir, destination_root):
    """
    Organize unsorted music files into proper folder structure.
    
    Args:
        source_dir (str): Source directory with unsorted files
        destination_root (str): Root directory where organized files should go
        
    Returns:
        dict: Statistics about the organization
    """
    if not os.path.exists(source_dir):
        safe_print(f"Error: Source directory does not exist: {source_dir}")
        return None
    
    if not os.path.isdir(source_dir):
        safe_print(f"Error: Source path is not a directory: {source_dir}")
        return None
    
    if not os.path.exists(destination_root):
        safe_print(f"Error: Destination root does not exist: {destination_root}")
        return None
    
    safe_print("=" * 60)
    safe_print("Organizing Unsorted Music Files")
    safe_print("=" * 60)
    safe_print(f"\nSource directory: {source_dir}")
    safe_print(f"Destination root: {destination_root}")
    safe_print("\nStep 1: Finding audio files...")
    
    # Find all audio files
    audio_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                full_path = os.path.join(root, file)
                audio_files.append(full_path)
    
    safe_print(f"Found {len(audio_files)} audio files")
    
    safe_print("\nStep 2: Processing files and organizing...")
    safe_print("This may take a while...\n")
    
    stats = {
        'files_processed': 0,
        'files_moved': 0,
        'files_skipped': 0,
        'folders_created': 0,
        'api_calls_made': 0,
        'errors': 0
    }
    
    # Track created folders to avoid duplicate creation
    created_folders = set()
    
    # Process each file
    for i, file_path in enumerate(audio_files, 1):
        if i % 10 == 0:
            safe_print(f"  Processed {i}/{len(audio_files)} files...")
        
        try:
            filename = os.path.basename(file_path)
            filename = safe_unicode_string(filename)
            
            # Read metadata tags from file (primary source)
            metadata = read_metadata_tags(file_path)
            
            # Extract metadata - prefer tags
            if metadata:
                artist_name = metadata.get('artist')
                track_name = metadata.get('title')
                album_name = metadata.get('album')
            else:
                artist_name = None
                track_name = None
                album_name = None
            
            # Fallback to filename if no track name from tags
            if not track_name:
                track_name = extract_track_name_from_filename(filename)
            
            # If we don't have artist or album, try API
            if (not artist_name or not album_name) and track_name:
                safe_print(f"\n[{i}/{len(audio_files)}] Missing metadata for: {filename}")
                safe_print(f"  Track name: {track_name}")
                safe_print(f"  Searching API for artist and album...")
                
                api_artist, api_album = get_album_artist_from_api(track_name)
                stats['api_calls_made'] += 1
                
                if api_artist:
                    artist_name = api_artist
                    safe_print(f"  ✓ Found artist: {artist_name}")
                else:
                    safe_print(f"  ✗ Could not find artist")
                
                if api_album:
                    album_name = api_album
                    safe_print(f"  ✓ Found album: {album_name}")
                else:
                    safe_print(f"  ✗ Could not find album")
            
            # If still no artist or album, skip this file
            if not artist_name:
                safe_print(f"  ⚠ Skipping {filename}: No artist information found")
                stats['files_skipped'] += 1
                continue
            
            if not album_name:
                album_name = "Unknown Album"
                safe_print(f"  ⚠ Using 'Unknown Album' for {filename}")
            
            # Sanitize artist and album names for filesystem
            artist_name = sanitize_filename(artist_name)
            album_name = sanitize_filename(album_name)
            
            # Create destination folder path
            dest_folder = os.path.join(destination_root, artist_name, album_name)
            dest_folder_clean = safe_unicode_string(dest_folder)
            if not dest_folder_clean:
                safe_print(f"  ✗ Error: Could not create valid folder path")
                stats['files_skipped'] += 1
                continue
            dest_folder = dest_folder_clean
            
            # Create folder if it doesn't exist
            folder_key = (artist_name, album_name)
            if folder_key not in created_folders:
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder, exist_ok=True)
                    stats['folders_created'] += 1
                    safe_print(f"  ✓ Created folder: {artist_name}/{album_name}")
                created_folders.add(folder_key)
            
            # Create destination file path
            filename_clean = safe_unicode_string(filename)
            if not filename_clean:
                safe_print(f"  ✗ Error: Could not create valid filename")
                stats['files_skipped'] += 1
                continue
            dest_file = os.path.join(dest_folder, filename_clean)
            
            # Check if file already exists at destination
            if os.path.exists(dest_file):
                # Generate unique filename
                base, ext = os.path.splitext(filename_clean)
                counter = 1
                while os.path.exists(dest_file):
                    new_filename = f"{base} ({counter}){ext}"
                    dest_file = os.path.join(dest_folder, new_filename)
                    counter += 1
                safe_print(f"  ⚠ File exists, using: {os.path.basename(dest_file)}")
            
            # Move file
            shutil.move(file_path, dest_file)
            stats['files_moved'] += 1
            stats['files_processed'] += 1
            
            safe_print(f"  ✓ Moved: {filename} → {artist_name}/{album_name}/")
            
        except Exception as e:
            safe_print(f"  ✗ Error processing {file_path}: {str(e)}")
            stats['errors'] += 1
            stats['files_skipped'] += 1
            continue
    
    return stats


def main():
    """
    Main function to organize unsorted music files.
    """
    # Source directory with unsorted files
    source_dir = "/home/stephen/Music/1 a not sorted"
    
    # Get destination root from database settings, fallback to Django settings
    db_settings = Settings.get_settings()
    destination_root = db_settings.root_music_path
    
    # Fallback to Django settings if database setting is empty
    if not destination_root:
        destination_root = getattr(django_settings, 'ROOT_MUSIC_PATH', '/home/stephen/Music')
    
    safe_print(f"Using destination root: {destination_root}")
    
    stats = organize_music_files(source_dir, destination_root)
    
    if stats:
        safe_print("\n" + "=" * 60)
        safe_print("Organization Complete!")
        safe_print("=" * 60)
        safe_print(f"\nSummary:")
        safe_print(f"  Files processed: {stats['files_processed']}")
        safe_print(f"  Files moved: {stats['files_moved']}")
        safe_print(f"  Files skipped: {stats['files_skipped']}")
        safe_print(f"  Folders created: {stats['folders_created']}")
        safe_print(f"  API calls made: {stats['api_calls_made']}")
        safe_print(f"  Errors: {stats['errors']}")
        safe_print(f"\nFiles have been organized into: {destination_root}/Artist/Album/")


if __name__ == '__main__':
    main()

