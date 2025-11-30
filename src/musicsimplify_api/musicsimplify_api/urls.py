from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/artistFetcher/', include('artistFetcher.urls')),
    path('api/downloader/', include('downloader.urls')),
    path('api/downloadManager/', include('downloadManager.urls')),
    path('api/loadCsv/', include('loadCsv.urls')),
    path('api/loadDisographies/', include('loadDisographies.urls')),
]
