from django.contrib import admin
from .models import Track, NewTrack


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre', 'download', 'failed_download')
    list_filter = ('download', 'failed_download', 'artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre')
    ordering = ('id',)


@admin.register(NewTrack)
class NewTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre')
    list_filter = ('artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre')
    ordering = ('artist_name', 'track_name')
