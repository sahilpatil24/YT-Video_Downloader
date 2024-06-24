# views.py
from django.shortcuts import render, HttpResponse
from django.http import StreamingHttpResponse, JsonResponse
from pytube import YouTube, Playlist
from .forms import VideoForm
import io
import zipfile
import threading
import time
import uuid

# Simulated storage for status updates
download_status = {}

def index(request):
    if request.method == 'POST':
        form = VideoForm(request.POST)
        if form.is_valid():
            vid_link = form.cleaned_data['link']
            yt = YouTube(vid_link)
            video = yt.streams.get_highest_resolution()

            # Download the video to an in-memory bytes buffer
            buffer = io.BytesIO()
            video.stream_to_buffer(buffer)
            buffer.seek(0)  # Rewind the buffer to the beginning

            # Define a generator to yield chunks of the video from the buffer
            def file_iterator(buffer, chunk_size=8192):
                while True:
                    chunk = buffer.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            response = StreamingHttpResponse(file_iterator(buffer))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="{yt.title}.mp4"'

            return response
    else:
        form = VideoForm()

    return render(request, 'index.html', {'form': form})

def credits(request):
    return render(request, 'credits.html')

def download_playlist(request):
    if request.method == 'POST':
        playlist_link = request.POST.get('playlist_link')
        playlist = Playlist(playlist_link)

        # Generate a unique ID for this download session
        session_id = str(uuid.uuid4())

        # Initialize the download status for this session
        download_status[session_id] = {
            'total_videos': len(playlist.video_urls),
            'downloaded_videos': 0,
            'current_video': '',
            'completed': False,
        }

        # Start the download process in a separate thread
        thread = threading.Thread(target=download_videos, args=(playlist, session_id))
        thread.start()

        return JsonResponse({'session_id': session_id})

    return render(request, 'download_playlist.html')

def download_videos(playlist, session_id):
    total_videos = len(playlist.video_urls)

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, video in enumerate(playlist.videos):
            download_status[session_id]['current_video'] = video.title
            video_buffer = io.BytesIO()
            stream = video.streams.get_highest_resolution()
            stream.stream_to_buffer(video_buffer)
            video_buffer.seek(0)

            # Write each video file to the zip archive
            zip_file.writestr(f"{video.title}.mp4", video_buffer.read())

            download_status[session_id]['downloaded_videos'] = i + 1

    zip_buffer.seek(0)
    download_status[session_id]['completed'] = True

    # Save the zip file to a more permanent location (optional)
    with open(f'/path/to/save/{session_id}.zip', 'wb') as f:
        f.write(zip_buffer.getvalue())

def get_download_status(request, session_id):
    status = download_status.get(session_id)
    if status:
        return JsonResponse(status)
    return JsonResponse({'error': 'Invalid session ID'}, status=400)
