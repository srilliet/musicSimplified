# Scripts

## process_collaborations.py

Processes artist collaborations in the database and fetches discographies for each collaborating artist.

### What it does:

1. Finds all tracks where `artist_name` contains `;` (collaborations)
2. Extracts unique artist names from these collaborations
3. For each artist, fetches their complete discography from Spotify/YouTube Music
4. Saves all tracks to the `new_tracks` table for future downloads

### Example:

If you have a track with `artist_name = "2pac;Big skye"`, the script will:
- Extract "2pac" and "Big skye" as separate artists
- Fetch all songs for "2pac"
- Fetch all songs for "Big skye"
- Save all discovered tracks to `new_tracks` table

### Usage:

From the project root directory:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the script
cd src/scripts
python process_collaborations.py
```

Or from anywhere:

```bash
source venv/bin/activate
python src/scripts/process_collaborations.py
```

### Requirements:

- Django environment must be set up
- Database must be initialized
- Spotify API credentials (optional, will fallback to YouTube Music if not configured)
- Environment variables (optional):
  - `SPOTIFY_CLIENT_ID`
  - `SPOTIFY_CLIENT_SECRET`

### Output:

The script will:
- Display progress for each artist
- Show statistics at the end:
  - Total artists processed
  - Successfully processed vs failed
  - Total tracks found
  - New tracks added
  - Duplicates skipped

### Notes:

- The script includes a 1-second delay between artists to avoid rate limiting
- Duplicate tracks (already in `new_tracks` table) are automatically skipped
- If an artist has no tracks found, it will be marked as failed but processing continues

## update_new_tracks.py

Re-checks all artists in the `new_tracks` table and adds missing tracks with improved pagination.

### What it does:

1. Gets all unique artists from the `new_tracks` table
2. Re-fetches complete discography for each artist (with improved pagination)
3. Adds only missing tracks (skips duplicates)
4. Should now return more than 100 tracks per artist with the fixed pagination

### Usage:

From the project root directory:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the script
cd src/scripts
python update_new_tracks.py
```

Or from anywhere:

```bash
source venv/bin/activate
python src/scripts/update_new_tracks.py
```

### Features:

- Only adds missing tracks (no duplicates)
- Shows which API was used (Spotify vs YouTube Music)
- Displays statistics including artists with 100+ tracks
- Improved pagination should fetch complete discographies
- Includes genre information when available from Spotify

### Output:

The script will:
- Display progress for each artist
- Show API used (Spotify/YouTube Music)
- Highlight when more than 100 tracks are found
- Show statistics at the end:
  - Total artists processed
  - Successfully processed vs failed
  - Total tracks found
  - New tracks added
  - Artists with 100+ tracks
  - API usage breakdown

### Notes:

- The script includes a 1-second delay between artists to avoid rate limiting
- Only missing tracks are added (existing tracks are skipped)
- With improved pagination, you should see more than 100 tracks per artist
- Genre information is included when fetching from Spotify

## update_genres.py

Updates genre information for tracks missing genre in both `tracks` and `new_tracks` tables.

### What it does:

1. Finds all tracks without genre in both `tracks` and `new_tracks` tables
2. Groups tracks by artist to minimize API calls
3. Fetches genre from Spotify API for each artist
4. Updates all tracks for that artist with the genre information

### Usage:

From the project root directory:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the script
cd src/scripts
python update_genres.py
```

Or from anywhere:

```bash
source venv/bin/activate
python src/scripts/update_genres.py
```

### Requirements:

- Spotify API credentials must be configured:
  ```bash
  export SPOTIFY_CLIENT_ID=your_client_id
  export SPOTIFY_CLIENT_SECRET=your_client_secret
  ```

### Features:

- Updates both `tracks` and `new_tracks` tables
- Groups by artist to minimize API calls
- Uses primary genre from Spotify artist information
- Only updates tracks that don't have genre (skips existing genres)

### Output:

The script will:
- Display progress for each artist
- Show genre found and number of tracks updated
- Show statistics at the end:
  - Total artists processed
  - Successfully processed vs failed
  - Tracks updated in each table
  - Total tracks updated

### Notes:

- The script includes a 0.2-second delay between artists to avoid rate limiting
- Only tracks without genre are updated (existing genres are preserved)
- If Spotify API is not configured, the script will exit with a warning

