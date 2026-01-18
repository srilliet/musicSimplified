from django.urls import path
from . import views

urlpatterns = [
    path('fetch/', views.fetch_artist_discography, name='fetch_artist_discography'),
    path('search/', views.search_artists, name='search_artists'),
]

