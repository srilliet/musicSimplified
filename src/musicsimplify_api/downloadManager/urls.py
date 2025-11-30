from django.urls import path
from . import views

urlpatterns = [
    path('download-all/', views.download_all_tracks, name='download_all_tracks'),
    path('stats/', views.get_download_stats, name='get_download_stats'),
]

