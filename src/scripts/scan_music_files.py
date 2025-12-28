#!/usr/bin/env python
"""
Script to scan music directory and add/update tracks in the database.

This script:
1. Scans the ROOT_MUSIC_PATH directory recursively for audio files
2. For each file found, searches the database for a matching track
3. If found: Updates track with relative_path and file_found status
4. If NOT found: Creates new track entry and fetches genre
5. Handles fuzzy matching for filenames that don't exactly match
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


def normalize_filename(filename):
    """
    Normalize a filename for matching purposes.
    
    Removes:
    - File extension
    - Track numbers (e.g., "01 - ", "00-", "1. ", etc.)
    - Extra whitespace
    - Special characters (normalizes them)
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Normalized filename
    """
    # Remove file extension
    name = os.path.splitext(filename)[0]
    
    # Remove track numbers at the start (e.g., "01 - ", "00-", "1. ", "001. ")
    name = re.sub(r'^\d+\s*[-.]?\s*', '', name, flags=re.IGNORECASE)
    
    # Normalize special characters
    name = name.replace('_', ' ')
    name = name.replace('&', 'and')
    name = name.replace('+', 'and')
    
    # Remove multiple spaces and strip
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Convert to lowercase for comparison
    return name.lower()


def normalize_artist_name(artist_name):
    """
    Normalize artist name for matching.
    
    Args:
        artist_name (str): Artist name
        
    Returns:
        str: Normalized artist name
    """
    if not artist_name:
        return ''
    
    # Normalize special characters
    name = artist_name.replace('&', 'and')
    name = name.replace('+', 'and')
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name.lower()


def similarity_score(str1, str2):
    """
    Calculate similarity score between two strings (0.0 to 1.0).
    
    Args:
        str1 (str): First string
        str2 (str): Second string
        
    Returns:
        float: Similarity score
    """
    return SequenceMatcher(None, str1, str2).ratio()


def extract_metadata_from_path(file_path, root_path):
    """
    Extract artist and album from the file path.
    
    Args:
        file_path (str): Full file path
        root_path (str): Root music directory path
        
    Returns:
        tuple: (artist_name, album_name) or (None, None)
    """
    try:
        # Get relative path
        rel_path = os.path.relpath(file_path, root_path)
        
        # Clean Unicode issues in path
        rel_path = safe_unicode_string(rel_path)
        
        if not rel_path:
            return None, None
        
        # Split path components
        parts = Path(rel_path).parts
        
        # First directory is often the artist
        artist = None
        album = None
        
        if len(parts) > 1:
            artist = safe_unicode_string(parts[0])
        if len(parts) > 2:
            album = safe_unicode_string(parts[1])
        
        return artist, album
    except:
        pass
    
    return None, None


def find_matching_track_in_db(normalized_filename, artist_name=None):
    """
    Find matching track in database using fuzzy matching.
    
    Args:
        normalized_filename (str): Normalized filename
        artist_name (str): Artist name (optional)
        
    Returns:
        tuple: (Track, score) or (None, score)
    """
    tracks = Track.objects.all()
    
    best_match = None
    best_score = 0.0
    
    for track in tracks:
        if not track.track_name:
            continue
        
        # Normalize track name
        normalized_track_name = normalize_filename(track.track_name)
        
        # Calculate similarity
        score = similarity_score(normalized_filename, normalized_track_name)
        
        # Bonus if artist matches
        if artist_name and track.artist_name:
            normalized_artist = normalize_artist_name(track.artist_name)
            normalized_file_artist = normalize_artist_name(artist_name)
            
            if normalized_artist == normalized_file_artist:
                score += 0.2  # Boost score if artist matches
            elif normalized_artist in normalized_file_artist or normalized_file_artist in normalized_artist:
                score += 0.1  # Partial artist match
        
        # Update best match
        if score > best_score:
            best_score = score
            best_match = track
    
    # Only return match if similarity is high enough (>= 0.7)
    if best_score >= 0.7:
        return best_match, best_score
    
    return None, best_score


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


def get_artist_genre_youtube_music(artist_name):
    """
    Try to fetch genre for an artist from YouTube Music.
    Note: YouTube Music doesn't directly provide genre, but we can try to infer
    from track categories or use a search-based approach.
    
    Args:
        artist_name (str): Name of the artist
        
    Returns:
        str: Genre or None if not found
    """
    try:
        ytmusic = YTMusic()
        
        search_results = ytmusic.search(query=artist_name, filter='artists', limit=1)
        
        if not search_results:
            return None
        
        artist_id = search_results[0].get('browseId')
        if not artist_id:
            return None
        
        try:
            search_tracks = ytmusic.search(query=f"{artist_name}", filter='songs', limit=5)
            
            if search_tracks:
                for track in search_tracks:
                    video_id = track.get('videoId')
                    if video_id:
                        try:
                            song_info = ytmusic.get_song(video_id)
                            category = song_info.get('category')
                            if category:
                                return category
                        except:
                            continue
        except:
            pass
        
        return None
    except Exception as e:
        return None


def fetch_genre_for_track(artist_name, track_name):
    """
    Fetch genre for a track, trying MusicBrainz first, then YouTube Music.
    
    Args:
        artist_name (str): Name of the artist
        track_name (str): Name of the track
        
    Returns:
        str: Primary genre or None if not found
    """
    if not artist_name or not track_name:
        return None
    
    genre = get_song_genre_musicbrainz(artist_name, track_name)
    if genre:
        return genre
    
    # Fallback to YouTube Music (less reliable for song-level)
    genre = get_artist_genre_youtube_music(artist_name)
    return genre


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


def scan_music_directory(root_path):
    """
    Scan music directory and add/update tracks in database.
    
    Args:
        root_path (str): Root music directory path
        
    Returns:
        dict: Statistics about the scan
    """
    if not os.path.exists(root_path):
        print(f"Error: Root path does not exist: {root_path}")
        return None
    
    if not os.path.isdir(root_path):
        print(f"Error: Root path is not a directory: {root_path}")
        return None
    
    safe_print("=" * 60)
    safe_print("Scanning Music Directory")
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
    
    safe_print("\nStep 2: Processing files and updating database...")
    safe_print("This may take a while...\n")
    
    stats = {
        'files_scanned': len(audio_files),
        'tracks_found_in_db': 0,
        'tracks_updated': 0,
        'tracks_created': 0,
        'tracks_with_genre_fetched': 0,
        'files_skipped': 0,
    }
    
    # Process each file
    for i, file_path in enumerate(audio_files, 1):
        if i % 100 == 0:
            safe_print(f"  Processed {i}/{len(audio_files)} files...")
        
        # Get relative path
        try:
            relative_path = os.path.relpath(file_path, root_path)
            # Clean Unicode issues
            relative_path = safe_unicode_string(relative_path)
        except:
            stats['files_skipped'] += 1
            continue
        
        # Read metadata tags from file (primary source)
        metadata = read_metadata_tags(file_path)
        
        # Extract metadata - prefer tags, fallback to filename/path
        if metadata:
            artist_name = metadata.get('artist')
            track_name = metadata.get('title')
            album_name = metadata.get('album')
            genre_from_tags = metadata.get('genre')
        else:
            artist_name = None
            track_name = None
            album_name = None
            genre_from_tags = None
        
        # Fallback to filename and path if tags are missing
        filename = os.path.basename(file_path)
        filename = safe_unicode_string(filename)
        normalized_filename = normalize_filename(filename)
        
        if not track_name:
            track_name = extract_track_name_from_filename(filename)
        
        # Extract artist and album from path as fallback
        artist_from_path, album_from_path = extract_metadata_from_path(file_path, root_path)
        artist_from_path = safe_unicode_string(artist_from_path) if artist_from_path else None
        album_from_path = safe_unicode_string(album_from_path) if album_from_path else None
        
        # Use metadata tags first, then path, then filename
        final_artist = artist_name or artist_from_path
        final_album = album_name or album_from_path
        
        # Search database for matching track
        matching_track, score = find_matching_track_in_db(
            normalized_filename if track_name else normalized_filename,
            final_artist
        )
        
        if matching_track:
            # Track found in database - update it
            stats['tracks_found_in_db'] += 1
            
            # Update file location if not already set or if this is a better match
            if not matching_track.relative_path or score >= 0.9:
                matching_track.relative_path = relative_path
                
                # Update artist/album if missing - prefer metadata tags over path
                if not matching_track.artist_name:
                    matching_track.artist_name = final_artist
                if not matching_track.album:
                    matching_track.album = final_album
                # Update genre if missing and we have it from tags
                if not matching_track.genre and genre_from_tags:
                    matching_track.genre = safe_unicode_string(genre_from_tags)
                
                matching_track.save()
                stats['tracks_updated'] += 1
        else:
            # Track NOT found - create new entry
            if not track_name:
                stats['files_skipped'] += 1
                continue
            
            # Create new track (ensure all strings are safe)
            new_track = Track(
                track_name=safe_unicode_string(track_name) if track_name else None,
                artist_name=safe_unicode_string(final_artist) if final_artist else None,
                album=safe_unicode_string(final_album) if final_album else None,
                relative_path=safe_unicode_string(relative_path) if relative_path else None,
                genre=safe_unicode_string(genre_from_tags) if genre_from_tags else None  # Use genre from tags if available
            )
            
            # Fetch genre if not in tags and we have artist name
            if not genre_from_tags and final_artist and track_name:
                safe_print(f"  Fetching genre for: {final_artist} - {track_name}")
                genre = fetch_genre_for_track(final_artist, track_name)
                if genre:
                    new_track.genre = safe_unicode_string(genre)
                    stats['tracks_with_genre_fetched'] += 1
                    safe_print(f"    ✓ Genre: {genre}")
                else:
                    safe_print(f"    ✗ No genre found")
            elif genre_from_tags:
                # Genre was found in tags
                stats['tracks_with_genre_fetched'] += 1
            
            new_track.save()
            stats['tracks_created'] += 1
    
    return stats


def main():
    """
    Main function to scan music directory and update database.
    """
    # Get root path from database settings, fallback to Django settings
    db_settings = Settings.get_settings()
    root_path = db_settings.root_music_path
    
    # Fallback to Django settings if database setting is empty
    if not root_path:
        root_path = getattr(django_settings, 'ROOT_MUSIC_PATH', '/home/stephen/Music')
    
    safe_print(f"Using root path from database: {root_path}")
    
    stats = scan_music_directory(root_path)
    
    if stats:
        safe_print("\n" + "=" * 60)
        safe_print("Scan Complete!")
        safe_print("=" * 60)
        safe_print(f"\nSummary:")
        safe_print(f"  Files scanned: {stats['files_scanned']}")
        safe_print(f"  Tracks found in database: {stats['tracks_found_in_db']}")
        safe_print(f"  Tracks updated: {stats['tracks_updated']}")
        safe_print(f"  New tracks created: {stats['tracks_created']}")
        safe_print(f"  Tracks with genre fetched: {stats['tracks_with_genre_fetched']}")
        safe_print(f"  Files skipped: {stats['files_skipped']}")
        safe_print("\nDatabase has been updated with file locations and new tracks.")
        safe_print(f"\nTo get full path: {root_path} + '/' + relative_path")


if __name__ == '__main__':
    main()
