# musicSimplified

A Django REST API application for managing and downloading music tracks from various sources.

## Features

- **Artist Discography Fetching**: Fetch complete discographies from Spotify and YouTube Music
- **CSV Import**: Load tracks from CSV files
- **Track Downloading**: Download tracks using yt-dlp or spotdl
- **Batch Download Management**: Manage bulk downloads with intelligent delay calculation
- **RESTful API**: Full REST API for all operations

## Requirements

- Python 3.12+
- Django 5.2+
- Django REST Framework 3.14+
- yt-dlp
- spotdl
- spotipy
- ytmusicapi

## Installation

1. Clone the repository:
```bash
git clone git@github.com:srilliet/musicSimplified.git
cd musicSimplified
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
cd src
pip install -r requirements.txt
```

4. Set up environment variables (optional, for Spotify API):
```bash
export SPOTIFY_CLIENT_ID=your_client_id
export SPOTIFY_CLIENT_SECRET=your_client_secret
```

5. Run migrations:
```bash
cd musicsimplify_api
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

## API Endpoints

### Artist Fetcher
- `GET/POST /api/artistFetcher/fetch/` - Fetch artist discography

### Downloader
- `POST /api/downloader/download/` - Download a track
- `GET /api/downloader/tracks/` - Get tracks list
- `GET /api/downloader/tracks/undownloaded-count/` - Get undownloaded count

### Download Manager
- `POST /api/downloadManager/download-all/` - Download all tracks
- `GET /api/downloadManager/stats/` - Get download statistics

### CSV Loader
- `POST /api/loadCsv/upload/` - Upload CSV file
- `POST /api/loadCsv/load-directory/` - Load CSV from directory

### Discography Loader
- `POST /api/loadDisographies/load-all/` - Load all discographies
- `POST /api/loadDisographies/load-artist/` - Load specific artist discography
- `GET /api/loadDisographies/new-tracks/` - Get new tracks

## Project Structure

```
MusicSimplify/
├── src/
│   ├── musicsimplify_api/          # Django project
│   │   ├── artistFetcher/          # Artist discography fetching
│   │   ├── downloader/             # Track downloading
│   │   ├── downloadManager/        # Batch download management
│   │   ├── loadCsv/                # CSV file loading
│   │   └── loadDisographies/       # Discography loading
│   ├── originalPythonfiles/        # Original Python scripts
│   └── requirements.txt
└── venv/                            # Virtual environment
```

## License

MIT

