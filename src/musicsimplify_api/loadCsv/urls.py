from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.load_csv_file, name='load_csv_file'),
    path('load-directory/', views.load_csv_from_directory, name='load_csv_from_directory'),
]

