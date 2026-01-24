from django.urls import path
from . import views

urlpatterns = [
    path('download/', views.download_track, name='download_track'),
    path('tracks/', views.get_tracks, name='get_tracks'),
    path('tracks/undownloaded-count/', views.get_undownloaded_count, name='get_undownloaded_count'),
    path('tracks/genres/', views.get_existing_tracks_genres, name='get_existing_tracks_genres'),
    path('tracks/artists/', views.get_existing_tracks_artists, name='get_existing_tracks_artists'),
    path('settings/', views.get_or_update_settings, name='get_or_update_settings'),
]

