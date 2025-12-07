# TODO - MusicBrainz API Integration

## MusicBrainz API Methods Reference

### Search Methods
- [ ] `search_artists()` - Search for artists
- [ ] `search_releases()` - Search for releases (albums/singles)
- [ ] `search_release_groups()` - Search for release groups
- [ ] `search_labels()` - Search for record labels
- [ ] `search_works()` - Search for musical works
- [ ] `search_places()` - Search for places (venues, studios)
- [ ] `search_events()` - Search for events (concerts, festivals)
- [ ] `search_instruments()` - Search for instruments
- [ ] `search_series()` - Search for series

### Get by ID Methods
- [ ] `get_artist_by_id()` - Get detailed artist info (with includes like releases, recordings, tags)
- [ ] `get_release_by_id()` - Get detailed release info
- [ ] `get_label_by_id()` - Get label info
- [ ] `get_work_by_id()` - Get musical work info
- [ ] `get_place_by_id()` - Get place info
- [ ] `get_event_by_id()` - Get event info
- [ ] `get_instrument_by_id()` - Get instrument info
- [ ] `get_series_by_id()` - Get series info

### Browse Methods (get related entities)
- [ ] `browse_releases()` - Browse releases by artist, label, etc.
- [ ] `browse_release_groups()` - Browse release groups by artist
- [ ] `browse_recordings()` - Browse recordings by artist, release, etc.
- [ ] `browse_works()` - Browse works by artist

### Includes (for detailed data)
When using `get_*_by_id()`, you can include:
- [ ] `'releases'` - Related releases
- [ ] `'recordings'` - Related recordings
- [x] `'tags'` - Genre tags (currently used in `update_genres.py`)
- [ ] `'ratings'` - User ratings
- [ ] `'aliases'` - Alternative names
- [ ] `'url-rels'` - External URLs
- [ ] `'work-rels'` - Related works
- [ ] `'artist-rels'` - Related artists
- [ ] `'release-group-rels'` - Related release groups

## Currently Used Methods
- [x] `search_recordings()` - Used in `update_genres.py` to find songs by artist and track name
- [x] `get_recording_by_id()` - Used in `update_genres.py` to get recording details with tags
- [x] `get_release_group_by_id()` - Used in `update_genres.py` as fallback for genre tags

## Potential Improvements for This Project

### High Priority
- [ ] **Alternative artist discography fetching**: Use `search_artists()` + `get_artist_by_id()` with `'releases'` include to get artist discography and metadata
- [ ] **Complete album track listings**: Use `browse_releases()` or `get_release_by_id()` to get track listing for specific albums
- [ ] **Better artist metadata**: Use `get_artist_by_id()` with `'aliases'` to handle artist name variations

### Medium Priority
- [ ] **Browse recordings by artist**: Use `browse_recordings()` to get all recordings for an artist (alternative to YouTube Music)
- [ ] **Release group information**: Use `browse_release_groups()` to get all albums/singles for an artist
- [ ] **External links**: Use `'url-rels'` include to get official artist websites, social media, etc.

### Low Priority
- [ ] **Event information**: Use `search_events()` to find concerts/festivals for artists
- [ ] **Label information**: Use `search_labels()` to get record label information
- [ ] **Work information**: Use `search_works()` to find musical compositions

## Notes
- All MusicBrainz API calls should maintain 2-second rate limiting to avoid getting banned
- Consider using MusicBrainz as a fallback or alternative to YouTube Music for discography fetching
- MusicBrainz provides more structured metadata but may have less coverage for newer/popular music
- Rate limit: 1 request per second (we use 2 seconds for safety)

## Implementation Ideas

### 1. Enhanced Artist Discography Fetcher
Replace or supplement YouTube Music with MusicBrainz:
```python
# Search for artist
result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
artist_id = result['artist-list'][0]['id']

# Get artist with all releases
artist_info = musicbrainzngs.get_artist_by_id(artist_id, includes=['releases', 'recordings', 'tags'])
```

### 2. Album Track Listing
Get complete track listing for albums:
```python
# Browse releases by artist
releases = musicbrainzngs.browse_releases(artist=artist_id, limit=100)

# Get detailed release info with track listing
for release in releases['release-list']:
    release_info = musicbrainzngs.get_release_by_id(release['id'], includes=['recordings'])
```

### 3. Genre Enhancement
Use multiple sources for genre:
- Recording tags (song-level) - currently implemented
- Release group tags (album-level) - currently implemented as fallback
- Artist tags (artist-level) - could add as another fallback

