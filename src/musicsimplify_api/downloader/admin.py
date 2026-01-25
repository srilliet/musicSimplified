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
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre', 'playcount', 'skipcount', 'relative_path')
    list_filter = ('artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre', 'relative_path')
    ordering = ('artist_name', 'track_name')
    readonly_fields = ('relative_path',)
    
    fieldsets = (
        ('Track Information', {
            'fields': ('track_name', 'artist_name', 'album', 'genre')
        }),
        ('Playback Statistics', {
            'fields': ('playcount', 'skipcount')
        }),
        ('File Information', {
            'fields': ('relative_path',)
        }),
    )


@admin.register(NewTrack)
class NewTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre', 'downloaded', 'success')
    list_filter = ('artist_name', 'genre', 'downloaded', 'success')
    search_fields = ('track_name', 'artist_name', 'album', 'genre')
    ordering = ('artist_name', 'track_name')
    
    fieldsets = (
        ('Track Information', {
            'fields': ('track_name', 'artist_name', 'album', 'genre')
        }),
        ('Download Status', {
            'fields': ('downloaded', 'success')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()