#!/usr/bin/env python
"""
Script to populate tracks table from music directory structure.

This script:
1. Scans /home/stephen/Music directory and subdirectories recursively
2. For each audio file found:
   - Extracts artist from folder structure (parent folder)
   - Extracts album from folder structure (grandparent folder)
   - Extracts song name from filename
   - Reads metadata tags from file (preferred source)
   - Uses folder structure as fallback if metadata missing
   - Uses API calls if both metadata and folder structure missing
3. Creates or updates tracks in the database
4. Fetches genre information if missing
"""

import os
import sys
import django
import re
import time
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'musicsimplify_api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')
django.setup()

from downloader.models import Track, Settings  # type: ignore
from django.conf import settings as django_settings
from django.db import models
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


def extract_from_folder_structure(file_path, root_path):
    """
    Extract artist, album, and track name from folder structure.
    
    Expected structure: root_path/Artist/Album/Song.mp3
    
    Args:
        file_path (str): Full path to audio file
        root_path (str): Root music directory path
        
    Returns:
        tuple: (artist_name, album_name, track_name) or (None, None, None)
    """
    try:
        # Get relative path from root
        rel_path = os.path.relpath(file_path, root_path)
        rel_path = safe_unicode_string(rel_path)
        
        if not rel_path:
            return None, None, None
        
        # Split path components
        parts = Path(rel_path).parts
        
        # Expected structure: Artist/Album/Song.mp3
        artist = None
        album = None
        track_name = None
        
        if len(parts) >= 3:
            # We have at least Artist/Album/Song
            artist = safe_unicode_string(parts[0])
            album = safe_unicode_string(parts[1])
            filename = safe_unicode_string(parts[-1])
            track_name = extract_track_name_from_filename(filename)
        elif len(parts) == 2:
            # We have Artist/Song (no album)
            artist = safe_unicode_string(parts[0])
            filename = safe_unicode_string(parts[-1])
            track_name = extract_track_name_from_filename(filename)
        elif len(parts) == 1:
            # Just Song (no artist/album folders)
            filename = safe_unicode_string(parts[0])
            track_name = extract_track_name_from_filename(filename)
        
        return artist, album, track_name
        
    except Exception as e:
        return None, None, None


def get_song_genre_musicbrainz(artist_name, track_name):
    """
    Fetch genre for a specific song from MusicBrainz API.
    Uses 2 second delay to respect rate limits and avoid getting banned.
    
    Args:
        artist_name (str): Name of the artist
        track_name (str): Name of the track
        
    Returns:
        str: Primary genre or None if not found
    """
    try:
        musicbrainzngs.set_useragent("MusicSimplify", "1.0", "https://github.com/srilliet/musicSimplified")
        
        # Search for recordings (songs) by artist and track name
        query = f'artist:"{artist_name}" AND recording:"{track_name}"'
        result = musicbrainzngs.search_recordings(query=query, limit=1)
        time.sleep(2)  # Rate limit: 2 seconds between API calls
        
        if not result.get('recording-list'):
            return None
        
        recording = result['recording-list'][0]
        recording_id = recording.get('id')
        
        if not recording_id:
            return None
        
        # Get detailed recording info with tags
        time.sleep(2)  # Rate limit: 2 seconds between API calls
        try:
            recording_info = musicbrainzngs.get_recording_by_id(recording_id, includes=['tags'])
            
            if 'tag-list' in recording_info.get('recording', {}):
                tags = recording_info['recording']['tag-list']
                if isinstance(tags, list) and len(tags) > 0:
                    if isinstance(tags[0], dict):
                        genre_tags = [tag.get('name', '') for tag in tags if tag.get('name')]
                    else:
                        genre_tags = [tags[0].get('name', '')] if isinstance(tags[0], dict) else []
                    if genre_tags:
                        return genre_tags[0]
        except:
            pass
        
        # Try release-group tags if recording tags not available
        if 'release-list' in recording and len(recording['release-list']) > 0:
            release = recording['release-list'][0]
            release_group_id = release.get('release-group', {}).get('id')
            
            if release_group_id:
                time.sleep(2)  # Rate limit: 2 seconds between API calls
                try:
                    release_group_info = musicbrainzngs.get_release_group_by_id(release_group_id, includes=['tags'])
                    
                    if 'tag-list' in release_group_info.get('release-group', {}):
                        tags = release_group_info['release-group']['tag-list']
                        if isinstance(tags, list) and len(tags) > 0:
                            if isinstance(tags[0], dict):
                                genre_tags = [tag.get('name', '') for tag in tags if tag.get('name')]
                            else:
                                genre_tags = [tags[0].get('name', '')] if isinstance(tags[0], dict) else []
                            if genre_tags:
                                return genre_tags[0]
                except:
                    pass
        
        return None
    except Exception as e:
        return None


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


def normalize_for_matching(text):
    """
    Normalize text for duplicate matching.
    Removes extra spaces, converts to lowercase, removes special characters.
    
    Args:
        text (str): Text to normalize
        
    Returns:
        str: Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = str(text).lower()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common punctuation that might differ
    text = text.replace('&', 'and')
    text = text.replace('+', 'and')
    text = text.replace('-', ' ')
    text = text.replace('_', ' ')
    
    # Remove extra spaces again
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def find_existing_track(artist_name, track_name, album_name=None, relative_path=None, stats=None):
    """
    Find existing track in database by BOTH relative_path AND track name.
    
    Only matches if BOTH conditions are true:
    1. Exact relative_path match (same file)
    2. Exact track name match (case-insensitive)
    
    This means:
    - Same file path + same track name = duplicate
    - Different file path + same track name = NOT duplicate (separate tracks)
    - Same file path + different track name = NOT duplicate (separate tracks)
    
    Args:
        artist_name (str): Artist name (not used for matching, only for reference)
        track_name (str): Track name (used for matching)
        album_name (str): Album name (not used for matching, only for reference)
        relative_path (str): Relative path (used for matching)
        stats (dict): Statistics dictionary to track match types (optional)
        
    Returns:
        tuple: (Track or None, match_type) where match_type is 'path_and_name' or None
    """
    if not track_name or not relative_path:
        return None, None
    
    # Only match if BOTH relative_path AND track name match
    tracks = Track.objects.filter(
        relative_path=relative_path,
        track_name__iexact=track_name
    )
    
    if tracks.exists():
        if stats:
            stats['duplicates_by_path'] += 1
        return tracks.first(), 'path_and_name'
    
    # Also try normalized track name matching for the same relative_path
    normalized_track = normalize_for_matching(track_name)
    
    if normalized_track:
        # Get all tracks with the same relative_path
        tracks_by_path = Track.objects.filter(relative_path=relative_path)
        
        for track in tracks_by_path:
            if track.track_name:
                track_name_norm = normalize_for_matching(track.track_name)
                
                # Match by normalized track name for the same path
                if track_name_norm == normalized_track:
                    if stats:
                        stats['duplicates_by_path'] += 1
                    return track, 'path_and_name_normalized'
    
    return None, None


def populate_tracks_from_directory(root_path):
    """
    Populate tracks table from music directory structure.
    
    Args:
        root_path (str): Root music directory path
        
    Returns:
        dict: Statistics about the operation
    """
    if not os.path.exists(root_path):
        safe_print(f"Error: Root path does not exist: {root_path}")
        return None
    
    if not os.path.isdir(root_path):
        safe_print(f"Error: Root path is not a directory: {root_path}")
        return None
    
    safe_print("=" * 60)
    safe_print("Populating Tracks from Directory")
    safe_print("=" * 60)
    safe_print(f"\nRoot path: {root_path}")
    safe_print("\nStep 1: Finding audio files...")
    
    # Find all audio files
    audio_files = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                full_path = os.path.join(root, file)
                audio_files.append(full_path)
    
    safe_print(f"Found {len(audio_files)} audio files")
    
    safe_print("\nStep 2: Processing files and populating database...")
    safe_print("This may take a while...\n")
    
    stats = {
        'files_found': len(audio_files),
        'files_processed': 0,
        'tracks_created': 0,
        'tracks_updated': 0,
        'tracks_already_exist': 0,  # Tracks that exist but don't need updates
        'tracks_skipped': 0,
        'duplicates_by_path': 0,  # Files that match by relative_path
        'duplicates_by_name': 0,  # Files that match by artist+track name
        'api_calls_made': 0,
        'genres_fetched': 0,
        'errors': 0
    }
    
    # Process each file
    for i, file_path in enumerate(audio_files, 1):
        if i % 100 == 0:
            safe_print(f"  Processed {i}/{len(audio_files)} files...")
        
        try:
            filename = os.path.basename(file_path)
            filename = safe_unicode_string(filename)
            
            # Get relative path
            relative_path = os.path.relpath(file_path, root_path)
            relative_path = safe_unicode_string(relative_path)
            
            # Read metadata tags from file (primary source)
            metadata = read_metadata_tags(file_path)
            
            # Extract from folder structure (fallback)
            folder_artist, folder_album, folder_track = extract_from_folder_structure(file_path, root_path)
            
            # Determine final values: prefer metadata, fallback to folder structure
            artist_name = None
            album_name = None
            track_name = None
            genre = None
            
            if metadata:
                artist_name = metadata.get('artist')
                track_name = metadata.get('title')
                album_name = metadata.get('album')
                genre = metadata.get('genre')
            
            # Fallback to folder structure
            if not artist_name:
                artist_name = folder_artist
            if not album_name:
                album_name = folder_album
            if not track_name:
                track_name = folder_track
            
            # If still missing, try API (only if we don't already have the info)
            # Check if we already have this track in database with complete info
            existing_track_check = None
            if track_name:
                existing_track_check, _ = find_existing_track(
                    artist_name=artist_name if artist_name else "Unknown Artist",
                    track_name=track_name,
                    album_name=album_name,
                    relative_path=relative_path,
                    stats=None  # Don't count this check in stats
                )
            
            # Only make API call if we're missing info AND don't have a complete existing track
            if (not artist_name or not album_name) and track_name:
                # If we have an existing track with complete info, use that instead of API
                if existing_track_check and existing_track_check.artist_name and existing_track_check.artist_name != "Unknown Artist":
                    if not artist_name:
                        artist_name = existing_track_check.artist_name
                        safe_print(f"  ✓ Using artist from existing track: {artist_name}")
                    if not album_name and existing_track_check.album:
                        album_name = existing_track_check.album
                        safe_print(f"  ✓ Using album from existing track: {album_name}")
                else:
                    # No existing track with complete info, make API call
                    safe_print(f"\n[{i}/{len(audio_files)}] Missing info for: {filename}")
                    safe_print(f"  Track: {track_name}")
                    api_artist, api_album = get_album_artist_from_api(track_name)
                    stats['api_calls_made'] += 1
                    
                    if api_artist and not artist_name:
                        artist_name = api_artist
                        safe_print(f"  ✓ Found artist: {artist_name}")
                    if api_album and not album_name:
                        album_name = api_album
                        safe_print(f"  ✓ Found album: {album_name}")
            
            # If still no track name, extract from filename (always use filename as fallback)
            if not track_name:
                track_name = extract_track_name_from_filename(filename)
            
            # Always use filename as track name if we still don't have one
            if not track_name and filename:
                # Last resort: use filename without extension
                filename_clean = safe_unicode_string(filename) or filename
                if filename_clean:
                    track_name = os.path.splitext(filename_clean)[0]
                    track_name = safe_unicode_string(track_name)
                    if track_name:
                        track_name = track_name.strip()
            
            # Use folder structure as fallback for artist/album if still missing
            if not artist_name:
                artist_name = folder_artist
            if not album_name:
                album_name = folder_album
            
            # Set defaults for missing info but still add to database
            if not track_name:
                # If we still can't get a track name, use filename
                track_name = filename
                safe_print(f"  ⚠ Using filename as track name: {filename}")
            
            if not artist_name:
                artist_name = "Unknown Artist"
            
            # Clean up track name one more time
            if track_name:
                track_name = track_name.strip()
                if not track_name:
                    track_name = filename  # Final fallback
            
            # Ensure we have at least track_name (should always have it by now)
            if not track_name:
                # Absolute last resort - this should rarely happen
                track_name = filename
                safe_print(f"  ⚠⚠ Using raw filename as track name: {filename}")
            
            # Find existing track using comprehensive duplicate detection
            existing_track, match_type = find_existing_track(
                artist_name=artist_name,
                track_name=track_name,
                album_name=album_name,
                relative_path=relative_path,
                stats=stats
            )
            
            if existing_track:
                # Update existing track with any new information
                updated = False
                
                # Always update relative_path if different (file location is most reliable)
                if relative_path and existing_track.relative_path != relative_path:
                    existing_track.relative_path = relative_path
                    updated = True
                
                # Update missing fields with new information
                if album_name and not existing_track.album:
                    existing_track.album = safe_unicode_string(album_name)
                    updated = True
                elif album_name and existing_track.album != album_name:
                    # If we have a better album name, update it
                    existing_track.album = safe_unicode_string(album_name)
                    updated = True
                
                if artist_name and not existing_track.artist_name:
                    existing_track.artist_name = safe_unicode_string(artist_name)
                    updated = True
                elif artist_name and existing_track.artist_name == "Unknown Artist" and artist_name != "Unknown Artist":
                    # Upgrade from Unknown Artist to actual artist
                    existing_track.artist_name = safe_unicode_string(artist_name)
                    updated = True
                
                if genre and not existing_track.genre:
                    existing_track.genre = safe_unicode_string(genre)
                    updated = True
                elif not existing_track.genre and artist_name and track_name and artist_name != "Unknown Artist":
                    # Try to find genre from other tracks with same artist/track
                    existing_with_genre = Track.objects.filter(
                        artist_name__iexact=artist_name,
                        track_name__iexact=track_name,
                        genre__isnull=False
                    ).exclude(genre='').exclude(id=existing_track.id).first()
                    
                    if existing_with_genre and existing_with_genre.genre:
                        # Use genre from another track
                        existing_track.genre = existing_with_genre.genre
                        updated = True
                        safe_print(f"  ✓ Using genre from another track: {existing_with_genre.genre}")
                    else:
                        # Make API call only if we don't have genre anywhere
                        safe_print(f"  Fetching genre for: {artist_name} - {track_name}")
                        fetched_genre = get_song_genre_musicbrainz(artist_name, track_name)
                        stats['api_calls_made'] += 1
                        if fetched_genre:
                            existing_track.genre = safe_unicode_string(fetched_genre)
                            updated = True
                            stats['genres_fetched'] += 1
                            safe_print(f"    ✓ Genre: {fetched_genre}")
                
                if updated:
                    existing_track.save()
                    stats['tracks_updated'] += 1
                else:
                    # Track exists and already has all info, no update needed
                    stats['tracks_already_exist'] += 1
            else:
                # Double-check for duplicates before creating (safety check)
                # This should rarely trigger since find_existing_track should catch it
                duplicate_check, _ = find_existing_track(
                    artist_name=artist_name,
                    track_name=track_name,
                    album_name=album_name,
                    relative_path=relative_path,
                    stats=None  # Don't double-count in stats
                )
                
                if duplicate_check:
                    # Found a duplicate we missed, update it instead
                    safe_print(f"  ⚠ Found duplicate, updating existing track instead")
                    existing_track = duplicate_check
                    updated = False
                    
                    if relative_path and existing_track.relative_path != relative_path:
                        existing_track.relative_path = relative_path
                        updated = True
                    if album_name and not existing_track.album:
                        existing_track.album = safe_unicode_string(album_name)
                        updated = True
                    if artist_name and existing_track.artist_name == "Unknown Artist" and artist_name != "Unknown Artist":
                        existing_track.artist_name = safe_unicode_string(artist_name)
                        updated = True
                    if genre and not existing_track.genre:
                        existing_track.genre = safe_unicode_string(genre)
                        updated = True
                    
                    if updated:
                        existing_track.save()
                        stats['tracks_updated'] += 1
                    else:
                        stats['tracks_already_exist'] += 1
                else:
                    # Create new track with whatever information we have
                    new_track = Track(
                        track_name=safe_unicode_string(track_name) if track_name else filename,
                        artist_name=safe_unicode_string(artist_name) if artist_name else "Unknown Artist",
                        album=safe_unicode_string(album_name) if album_name else None,
                        relative_path=safe_unicode_string(relative_path) if relative_path else None,
                        genre=safe_unicode_string(genre) if genre else None
                    )
                    
                    # Fetch genre if missing and we have artist and track name
                    # First check if we have an existing track with genre we can use
                    if not genre and artist_name and track_name and artist_name != "Unknown Artist":
                        # Check if there's an existing track with the same artist/track that has genre
                        existing_with_genre = Track.objects.filter(
                            artist_name__iexact=artist_name,
                            track_name__iexact=track_name,
                            genre__isnull=False
                        ).exclude(genre='').first()
                        
                        if existing_with_genre and existing_with_genre.genre:
                            # Use genre from existing track
                            new_track.genre = existing_with_genre.genre
                            stats['genres_fetched'] += 1
                            safe_print(f"  ✓ Using genre from existing track: {existing_with_genre.genre}")
                        else:
                            # No existing genre found, make API call
                            safe_print(f"  Fetching genre for: {artist_name} - {track_name}")
                            fetched_genre = get_song_genre_musicbrainz(artist_name, track_name)
                            stats['api_calls_made'] += 1
                            if fetched_genre:
                                new_track.genre = safe_unicode_string(fetched_genre)
                                stats['genres_fetched'] += 1
                                safe_print(f"    ✓ Genre: {fetched_genre}")
                    
                    new_track.save()
                    stats['tracks_created'] += 1
            
            stats['files_processed'] += 1
            
        except Exception as e:
            safe_print(f"  ✗ Error processing {file_path}: {str(e)}")
            stats['errors'] += 1
            stats['tracks_skipped'] += 1
            continue
    
    return stats


def main():
    """
    Main function to populate tracks from directory.
    """
    # Root music directory
    root_path = "/home/stephen/Music"
    
    # Get from database settings if available, otherwise use default
    try:
        db_settings = Settings.get_settings()
        if db_settings.root_music_path:
            root_path = db_settings.root_music_path
    except:
        pass
    
    # Fallback to Django settings
    if not root_path or not os.path.exists(root_path):
        root_path = getattr(django_settings, 'ROOT_MUSIC_PATH', '/home/stephen/Music')
    
    safe_print(f"Using root path: {root_path}")
    
    stats = populate_tracks_from_directory(root_path)
    
    if stats:
        safe_print("\n" + "=" * 60)
        safe_print("Population Complete!")
        safe_print("=" * 60)
        safe_print(f"\nSummary:")
        safe_print(f"  Files found: {stats['files_found']}")
        safe_print(f"  Files processed: {stats['files_processed']}")
        safe_print(f"  Tracks created: {stats['tracks_created']}")
        safe_print(f"  Tracks updated: {stats['tracks_updated']}")
        safe_print(f"  Tracks already exist (no update needed): {stats['tracks_already_exist']}")
        safe_print(f"  Tracks skipped: {stats['tracks_skipped']}")
        safe_print(f"  Duplicates matched by path: {stats['duplicates_by_path']}")
        safe_print(f"  Duplicates matched by name: {stats['duplicates_by_name']}")
        safe_print(f"  API calls made: {stats['api_calls_made']}")
        safe_print(f"  Genres fetched: {stats['genres_fetched']}")
        safe_print(f"  Errors: {stats['errors']}")
        safe_print(f"\nTotal tracks accounted for: {stats['tracks_created'] + stats['tracks_updated'] + stats['tracks_already_exist']}")
        safe_print(f"Files not processed: {stats['files_found'] - stats['files_processed']}")
        safe_print(f"\nNote: If files found ({stats['files_found']}) > tracks created ({stats['tracks_created']}),")
        safe_print(f"      it means many files matched existing tracks (duplicates).")
        safe_print(f"      This is normal if you're re-running the script or have duplicate files.")
        safe_print(f"\nDatabase has been populated with track information.")


if __name__ == '__main__':
    main()

