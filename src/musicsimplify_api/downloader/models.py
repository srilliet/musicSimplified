from django.db import models


class Track(models.Model):
    id = models.AutoField(primary_key=True)
    track_name = models.CharField(max_length=500)
    album = models.CharField(max_length=500, blank=True, null=True)
    artist_name = models.CharField(max_length=500, blank=True, null=True)
    genre = models.CharField(max_length=200, blank=True, null=True)
    download = models.IntegerField(default=0)
    failed_download = models.IntegerField(default=0)
    
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
    
    class Meta:
        db_table = 'new_tracks'
    
    def __str__(self):
        return f"{self.artist_name} - {self.track_name}"
