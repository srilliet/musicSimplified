from django.urls import path
from . import views

urlpatterns = [
    path('load-all/', views.load_all_discographies, name='load_all_discographies'),
    path('load-artist/', views.load_artist_discography, name='load_artist_discography'),
    path('new-tracks/', views.get_new_tracks, name='get_new_tracks'),
    path('genres/', views.get_genres, name='get_genres'),
]

