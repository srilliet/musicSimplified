from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Settings(models.Model):
    """
    Application settings stored in the database.
    Singleton pattern - only one settings record should exist.
    """
    id = models.AutoField(primary_key=True)
    root_music_path = models.CharField(
        max_length=1000,
        default='/home/stephen/Music',
        help_text='Root directory where music files are stored'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'settings'
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'
    
    def __str__(self):
        return f"Settings (Root: {self.root_music_path})"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings record exists
        if not self.pk and Settings.objects.exists():
            raise ValidationError('Only one settings record is allowed. Please update the existing one.')
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the settings instance, creating one if it doesn't exist."""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={'root_music_path': '/home/stephen/Music'}
        )
        return settings


class Track(models.Model):
    id = models.AutoField(primary_key=True)
    track_name = models.CharField(max_length=500)
    album = models.CharField(max_length=500, blank=True, null=True)
    artist_name = models.CharField(max_length=500, blank=True, null=True)
    genre = models.CharField(max_length=200, blank=True, null=True)
    relative_path = models.CharField(max_length=1000, blank=True, null=True)  # Relative path from root, e.g., "Zakk Wylde/book of shadows/between heaven & hell.mp3"
    
    class Meta:
        db_table = 'tracks'
    
    def __str__(self):
        return f"{self.artist_name} - {self.track_name}"


class UserTrack(models.Model):
    """
    User-specific track library and statistics.
    Links users to tracks and tracks removal status and playback statistics.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='user_tracks')
    is_removed = models.BooleanField(default=False)  # True if user removed from their library
    playcount = models.IntegerField(default=0)  # User-specific play count
    skipcount = models.IntegerField(default=0)  # User-specific skip count
    # Dynamic playlist fields
    rating = models.IntegerField(
        null=True, 
        blank=True, 
        help_text='User rating 1-5 stars',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # 1-5 rating
    favorite = models.BooleanField(default=False)  # Favorite/liked flag
    last_played = models.DateTimeField(null=True, blank=True)  # Last time track was played
    play_streak = models.IntegerField(default=0)  # Current consecutive plays without skip
    added_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_tracks'
        unique_together = [['user', 'track']]  # One record per user-track pair
        indexes = [
            models.Index(fields=['user', 'is_removed']),
            models.Index(fields=['user', 'track']),
            models.Index(fields=['user', 'favorite']),
            models.Index(fields=['user', 'rating']),
            models.Index(fields=['user', 'last_played']),
        ]
    
    @property
    def skip_ratio(self):
        """Calculate skip ratio for dynamic playlists (0.0 to 1.0)"""
        if self.playcount == 0:
            return 0.0
        return round(self.skipcount / self.playcount, 2)
    
    def clean(self):
        """Validate rating is between 1-5 if provided"""
        if self.rating is not None and (self.rating < 1 or self.rating > 5):
            raise ValidationError({'rating': 'Rating must be between 1 and 5'})
    
    def __str__(self):
        return f"{self.user.username} - {self.track.track_name}"


class NewTrack(models.Model):
    id = models.AutoField(primary_key=True)
    artist_name = models.CharField(max_length=500)
    track_name = models.CharField(max_length=500)
    album = models.CharField(max_length=500, blank=True, null=True)
    genre = models.CharField(max_length=200, blank=True, null=True)
    downloaded = models.BooleanField(default=False)  # Track if download was attempted
    success = models.BooleanField(default=False)  # Track if download was successful
    
    class Meta:
        db_table = 'new_tracks'
    
    def __str__(self):
        return f"{self.artist_name} - {self.track_name}"


class Playlist(models.Model):
    """
    User-created playlists.
    Each user can create multiple playlists with custom names.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=200, help_text='Playlist name')
    description = models.TextField(blank=True, null=True, help_text='Optional playlist description')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'playlists'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PlaylistTrack(models.Model):
    """
    Links tracks to playlists (many-to-many relationship).
    Maintains track order within each playlist.
    """
    id = models.AutoField(primary_key=True)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='playlist_tracks')
    position = models.IntegerField(default=0, help_text='Track position/order in playlist')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'playlist_tracks'
        unique_together = [['playlist', 'track']]  # Prevent duplicate tracks in same playlist
        indexes = [
            models.Index(fields=['playlist', 'position']),
            models.Index(fields=['playlist', 'track']),
        ]
        ordering = ['playlist', 'position', 'added_at']
    
    def __str__(self):
        return f"{self.playlist.name} - {self.track.track_name} (Position: {self.position})"
