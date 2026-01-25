from django.contrib import admin
from .models import Track, NewTrack, Settings, UserTrack, Playlist, PlaylistTrack


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
    list_display = ('id', 'track_name', 'artist_name', 'album', 'genre', 'relative_path')
    list_filter = ('artist_name', 'genre')
    search_fields = ('track_name', 'artist_name', 'album', 'genre', 'relative_path')
    ordering = ('artist_name', 'track_name')
    readonly_fields = ('relative_path',)
    
    fieldsets = (
        ('Track Information', {
            'fields': ('track_name', 'artist_name', 'album', 'genre')
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


@admin.register(UserTrack)
class UserTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'track', 'is_removed', 'favorite', 'rating', 'playcount', 'skipcount', 'play_streak', 'last_played', 'added_at')
    list_filter = ('is_removed', 'favorite', 'rating', 'user', 'added_at', 'last_played')
    search_fields = ('user__username', 'track__track_name', 'track__artist_name')
    ordering = ('-added_at',)
    readonly_fields = ('added_at',)
    
    fieldsets = (
        ('User & Track', {
            'fields': ('user', 'track')
        }),
        ('Library Status', {
            'fields': ('is_removed', 'removed_at')
        }),
        ('Playback Statistics', {
            'fields': ('playcount', 'skipcount', 'play_streak', 'last_played'),
            'description': 'Skip ratio is calculated as skipcount/playcount (read-only, calculated property)'
        }),
        ('Dynamic Playlist Fields', {
            'fields': ('rating', 'favorite')
        }),
        ('Timestamps', {
            'fields': ('added_at',)
        }),
    )
    
    def skip_ratio(self, obj):
        return obj.skip_ratio
    skip_ratio.short_description = 'Skip Ratio'


class PlaylistTrackInline(admin.TabularInline):
    """Inline admin for managing tracks within a playlist"""
    model = PlaylistTrack
    extra = 1
    fields = ('track', 'position')
    ordering = ('position', 'added_at')


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'track_count', 'created_at', 'updated_at')
    list_filter = ('user', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'user__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlaylistTrackInline]
    
    fieldsets = (
        ('Playlist Information', {
            'fields': ('user', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def track_count(self, obj):
        """Display the number of tracks in the playlist"""
        return obj.playlist_tracks.count()
    track_count.short_description = 'Track Count'


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'playlist', 'track', 'position', 'added_at')
    list_filter = ('playlist', 'playlist__user', 'added_at')
    search_fields = ('playlist__name', 'track__track_name', 'track__artist_name')
    ordering = ('playlist', 'position', 'added_at')
    readonly_fields = ('added_at',)
    
    fieldsets = (
        ('Playlist & Track', {
            'fields': ('playlist', 'track', 'position')
        }),
        ('Timestamps', {
            'fields': ('added_at',)
        }),
    )