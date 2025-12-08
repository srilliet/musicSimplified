from django.urls import path
from . import views

urlpatterns = [
    path('download/', views.download_track, name='download_track'),
    path('tracks/', views.get_tracks, name='get_tracks'),
    path('tracks/undownloaded-count/', views.get_undownloaded_count, name='get_undownloaded_count'),
    path('settings/', views.get_or_update_settings, name='get_or_update_settings'),
]

