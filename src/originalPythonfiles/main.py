import os
import sys
from database import init_database
from load_csv import load_csv_files
from download_manager import download_all_tracks
from load_discographies import load_all_discographies

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    download_dir = os.path.join(project_root, 'downloads')
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'download':
            print("Starting download process...")
            download_all_tracks(download_dir)
        elif sys.argv[1] == 'fetch-artists':
            print("Initializing database...")
            init_database()
            print("Fetching artist discographies...\n")
            load_all_discographies()
        else:
            print("Unknown command. Available commands:")
            print("  - (no args)     : Load CSV files")
            print("  - download      : Download tracks")
            print("  - fetch-artists  : Fetch all songs for artists in database")
    else:
        print("Initializing database...")
        init_database()
        print("Database initialized.")
        
        print(f"\nLoading CSV files from {project_root}...")
        total_inserted = load_csv_files(project_root)
        
        print(f"\nTotal tracks inserted: {total_inserted}")
        print("\nAvailable commands:")
        print("  - python src/main.py download      : Download tracks")
        print("  - python src/main.py fetch-artists : Fetch all songs for artists")

if __name__ == '__main__':
    main()

