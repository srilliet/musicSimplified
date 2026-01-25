from django.urls import path
from . import views
from . import user_tracks_views

urlpatterns = [
    path('download/', views.download_track, name='download_track'),
    path('tracks/', views.get_tracks, name='get_tracks'),
    path('tracks/undownloaded-count/', views.get_undownloaded_count, name='get_undownloaded_count'),
    path('tracks/genres/', views.get_existing_tracks_genres, name='get_existing_tracks_genres'),
    path('tracks/artists/', views.get_existing_tracks_artists, name='get_existing_tracks_artists'),
    path('settings/', views.get_or_update_settings, name='get_or_update_settings'),
    # User tracks endpoints
    path('user-tracks/', user_tracks_views.get_user_tracks, name='get_user_tracks'),
    path('user-tracks/initialize/', user_tracks_views.initialize_user_library, name='initialize_user_library'),
    path('user-tracks/<int:track_id>/remove/', user_tracks_views.remove_track_from_library, name='remove_track_from_library'),
    path('user-tracks/<int:track_id>/restore/', user_tracks_views.restore_track_to_library, name='restore_track_to_library'),
    path('user-tracks/genres/', user_tracks_views.get_user_tracks_genres, name='get_user_tracks_genres'),
    path('user-tracks/artists/', user_tracks_views.get_user_tracks_artists, name='get_user_tracks_artists'),
]

