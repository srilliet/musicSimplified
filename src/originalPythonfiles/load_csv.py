import csv
import os
import sqlite3
from database import get_connection, track_exists

def load_csv_files(main_dir):
    csv_files = [f for f in os.listdir(main_dir) if f.endswith('.csv')]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    total_inserted = 0
    total_skipped = 0
    
    for csv_file in csv_files:
        csv_path = os.path.join(main_dir, csv_file)
        print(f"Processing {csv_file}...")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                inserted_count = 0
                skipped_count = 0
                
                for row in reader:
                    track_name = row.get('Track Name', '').strip()
                    album = row.get('Album Name', '').strip()
                    artist_name = row.get('Artist Name(s)', '').strip()
                    
                    if track_name:
                        if not track_exists(track_name, artist_name):
                            cursor.execute('''
                                INSERT INTO tracks (track_name, album, artist_name, download, failed_download)
                                VALUES (?, ?, ?, 0, 0)
                            ''', (track_name, album, artist_name))
                            inserted_count += 1
                        else:
                            skipped_count += 1
                
                conn.commit()
                total_inserted += inserted_count
                total_skipped += skipped_count
                print(f"  Inserted {inserted_count} tracks from {csv_file}")
                if skipped_count > 0:
                    print(f"  Skipped {skipped_count} duplicate tracks")
                
                os.remove(csv_path)
                print(f"  Deleted {csv_file}")
        
        except Exception as e:
            print(f"  Error processing {csv_file}: {e}")
    
    conn.close()
    print(f"\nTotal inserted: {total_inserted}")
    if total_skipped > 0:
        print(f"Total skipped (duplicates): {total_skipped}")
    return total_inserted

