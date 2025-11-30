import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'music_riper.db')

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_name TEXT NOT NULL,
            album TEXT,
            artist_name TEXT,
            download INTEGER DEFAULT 0,
            failed_download INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_name TEXT NOT NULL,
            track_name TEXT NOT NULL,
            album TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_undownloaded_tracks(limit=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT id, track_name, album, artist_name 
        FROM tracks 
        WHERE download = 0 AND failed_download = 0
        ORDER BY id
    '''
    if limit:
        query += f' LIMIT {limit}'
    cursor.execute(query)
    tracks = cursor.fetchall()
    conn.close()
    return tracks

def count_undownloaded_tracks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) 
        FROM tracks 
        WHERE download = 0 AND failed_download = 0
    ''')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def update_download_status(track_id, success=True):
    conn = get_connection()
    cursor = conn.cursor()
    if success:
        cursor.execute('''
            UPDATE tracks 
            SET download = 1, failed_download = 0 
            WHERE id = ?
        ''', (track_id,))
    else:
        cursor.execute('''
            UPDATE tracks 
            SET failed_download = 1 
            WHERE id = ?
        ''', (track_id,))
    conn.commit()
    conn.close()

def track_exists(track_name, artist_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) 
        FROM tracks 
        WHERE track_name = ? AND artist_name = ?
    ''', (track_name, artist_name))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_all_artists():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT artist_name 
        FROM tracks 
        WHERE artist_name IS NOT NULL AND artist_name != ''
        ORDER BY artist_name
    ''')
    artists = [row[0] for row in cursor.fetchall()]
    conn.close()
    return artists

def add_new_track(artist_name, track_name, album=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO new_tracks (artist_name, track_name, album)
        VALUES (?, ?, ?)
    ''', (artist_name, track_name, album))
    conn.commit()
    conn.close()

def new_track_exists(artist_name, track_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) 
        FROM new_tracks 
        WHERE track_name = ? AND artist_name = ?
    ''', (track_name, artist_name))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_new_tracks(artist_name=None):
    conn = get_connection()
    cursor = conn.cursor()
    if artist_name:
        cursor.execute('''
            SELECT id, artist_name, track_name, album 
            FROM new_tracks 
            WHERE artist_name = ?
            ORDER BY track_name
        ''', (artist_name,))
    else:
        cursor.execute('''
            SELECT id, artist_name, track_name, album 
            FROM new_tracks 
            ORDER BY artist_name, track_name
        ''')
    tracks = cursor.fetchall()
    conn.close()
    return tracks

