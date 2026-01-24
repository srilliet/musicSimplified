from django.db import models
from django.core.exceptions import ValidationError


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
    playcount = models.IntegerField(default=0)
    skipcount = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'tracks'
    
    def __str__(self):
        return f"{self.artist_name} - {self.track_name}"


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
