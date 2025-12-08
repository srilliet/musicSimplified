from django.contrib import admin
from .models import Track, NewTrack, Settings


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'root_music_path', 'updated_at')
    fields = ('root_music_path', 'updated_at')
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Only allow adding if no settings exist
        return not Settings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre', 'file_found', 'download', 'failed_download')
    list_filter = ('download', 'failed_download', 'file_found', 'artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre', 'relative_path')
    ordering = ('id',)
    readonly_fields = ('relative_path',) if 'relative_path' in [f.name for f in Track._meta.get_fields()] else ()


@admin.register(NewTrack)
class NewTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre')
    list_filter = ('artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre')
    ordering = ('artist_name', 'track_name')
