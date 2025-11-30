import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import time

def get_spotify_client():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        return sp
    except Exception as e:
        return None

def fetch_artist_discography_youtube_music(artist_name):
    try:
        from ytmusicapi import YTMusic
        ytmusic = YTMusic()
        
        search_results = ytmusic.search(query=artist_name, filter='artists', limit=1)
        
        if not search_results:
            return []
        
        artist_id = search_results[0].get('browseId')
        if not artist_id:
            return []
        
        try:
            artist_albums = ytmusic.get_artist_albums(browseId=artist_id, limit=100)
        except:
            artist_albums = []
        
        tracks = []
        for album in artist_albums:
            album_name = album.get('title', '')
            album_id = album.get('browseId')
            
            if album_id:
                try:
                    album_tracks = ytmusic.get_album(browseId=album_id)
                    for track in album_tracks.get('tracks', []):
                        track_name = track.get('title', '')
                        if track_name:
                            tracks.append((track_name, album_name, artist_name))
                    time.sleep(0.3)
                except:
                    continue
        
        if not tracks:
            search_tracks = ytmusic.search(query=f"{artist_name}", filter='songs', limit=100)
            for track in search_tracks:
                track_name = track.get('title', '')
                album_name = track.get('album', {}).get('name', '') if track.get('album') else ''
                if track_name:
                    tracks.append((track_name, album_name, artist_name))
        
        return tracks
    except Exception as e:
        return []

def fetch_artist_discography_spotify(artist_name, spotify_client):
    try:
        results = spotify_client.search(q=f'artist:{artist_name}', type='artist', limit=1)
        
        if not results['artists']['items']:
            return []
        
        artist = results['artists']['items'][0]
        artist_id = artist['id']
        
        albums = []
        offset = 0
        limit = 50
        
        while True:
            results = spotify_client.artist_albums(artist_id, album_type='album,single', limit=limit, offset=offset)
            albums.extend(results['items'])
            
            if len(results['items']) < limit:
                break
            offset += limit
            time.sleep(0.2)
        
        tracks = []
        for album in albums:
            album_name = album['name']
            album_id = album['id']
            
            album_tracks = spotify_client.album_tracks(album_id, limit=50)
            
            for item in album_tracks['items']:
                track_name = item['name']
                tracks.append((track_name, album_name, artist_name))
            
            time.sleep(0.2)
        
        return tracks
    except Exception as e:
        return []

def fetch_artist_discography(artist_name):
    spotify_client = get_spotify_client()
    
    if spotify_client:
        try:
            tracks = fetch_artist_discography_spotify(artist_name, spotify_client)
            if tracks:
                return tracks
        except Exception as e:
            pass
    
    tracks = fetch_artist_discography_youtube_music(artist_name)
    if tracks:
        return tracks
    
    return []

