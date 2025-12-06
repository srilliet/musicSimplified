import csv
import os
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from downloader.models import Track


@api_view(['POST'])
def load_csv_file(request):
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No CSV file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    csv_file = request.FILES['file']
    
    if not csv_file.name.endswith('.csv'):
        return Response(
            {'error': 'File must be a CSV file'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
        header = next(csv_data)
        
        inserted_count = 0
        skipped_count = 0
        
        for row in csv.DictReader(decoded_file.splitlines()):
            track_name = row.get('Track Name', '').strip()
            album = row.get('Album Name', '').strip()
            artist_name = row.get('Artist Name(s)', '').strip()
            genre = row.get('Genre', '').strip()
            
            if track_name:
                if not Track.objects.filter(track_name=track_name, artist_name=artist_name).exists():
                    Track.objects.create(
                        track_name=track_name,
                        album=album if album else None,
                        artist_name=artist_name if artist_name else None,
                        genre=genre if genre else None,
                        download=0,
                        failed_download=0
                    )
                    inserted_count += 1
                else:
                    skipped_count += 1
        
        return Response({
            'message': 'CSV file processed successfully',
            'inserted': inserted_count,
            'skipped': skipped_count
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Error processing CSV file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def load_csv_from_directory(request):
    directory_path = request.data.get('directory_path', None)
    
    if not directory_path:
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        directory_path = str(project_root)
    
    if not os.path.isdir(directory_path):
        return Response(
            {'error': 'Directory does not exist'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    
    if not csv_files:
        return Response({
            'message': 'No CSV files found in directory',
            'inserted': 0,
            'skipped': 0
        }, status=status.HTTP_200_OK)
    
    total_inserted = 0
    total_skipped = 0
    
    for csv_file in csv_files:
        csv_path = os.path.join(directory_path, csv_file)
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                inserted_count = 0
                skipped_count = 0
                
                for row in reader:
                    track_name = row.get('Track Name', '').strip()
                    album = row.get('Album Name', '').strip()
                    artist_name = row.get('Artist Name(s)', '').strip()
                    genre = row.get('Genre', '').strip()
                    
                    if track_name:
                        if not Track.objects.filter(track_name=track_name, artist_name=artist_name).exists():
                            Track.objects.create(
                                track_name=track_name,
                                album=album if album else None,
                                artist_name=artist_name if artist_name else None,
                                genre=genre if genre else None,
                                download=0,
                                failed_download=0
                            )
                            inserted_count += 1
                        else:
                            skipped_count += 1
                
                total_inserted += inserted_count
                total_skipped += skipped_count
                
                os.remove(csv_path)
        
        except Exception as e:
            continue
    
    return Response({
        'message': 'CSV files processed successfully',
        'files_processed': len(csv_files),
        'inserted': total_inserted,
        'skipped': total_skipped
    }, status=status.HTTP_200_OK)
