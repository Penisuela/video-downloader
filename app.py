from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os
import yt_dlp
import re
import uuid
from flask import send_file
from threading import Thread
from time import sleep
from pytube import YouTube
import datetime

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

progress_dict = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def is_supported_url(url):
    youtube_pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+'
    tiktok_pattern = r'^(https?://)?((?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)$'
    instagram_pattern = r'^(https?://)?((?:www\.)?instagram\.com/(?:p|reel|tv|reels|stories)/[a-zA-Z0-9_-]+(?:/\?.*)?|instagram\.com/[^/]+/[^/]+)$'
    return bool(re.match(youtube_pattern, url) or re.match(tiktok_pattern, url) or re.match(instagram_pattern, url))

def get_browser_cookies():
    browsers = [
        ('chrome',),
        ('firefox',),
        ('safari',),
        ('edge',),
        ('opera',),
        ('brave',),
    ]
    
    for browser in browsers:
        try:
            return {'cookiesfrombrowser': browser}
        except:
            continue
    return {}  # Если ни один браузер не найден, возвращаем пустой словарь

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')
    if not url:
        return jsonify({'error': 'Не передан URL'}), 400
    task_id = str(uuid.uuid4())
    progress_dict[task_id] = {'progress': 0.0, 'status': 'downloading', 'file_url': None, 'error': None}

    def run_download():
        try:
            save_path = os.path.join('static', 'downloads')
            os.makedirs(save_path, exist_ok=True)
            
            yt = YouTube(url)
            
            if format_id:
                stream = yt.streams.get_by_itag(int(format_id))
            else:
                stream = yt.streams.get_highest_resolution()
                
            if not stream:
                progress_dict[task_id]['status'] = 'error'
                progress_dict[task_id]['error'] = 'Не удалось найти подходящий формат'
                return
                
            # Скачиваем файл
            filename = stream.download(output_path=save_path)
            
            # Если это аудио, конвертируем в mp3
            if stream.mime_type.startswith('audio'):
                base, _ = os.path.splitext(filename)
                new_filename = base + '.mp3'
                os.rename(filename, new_filename)
                filename = new_filename
            
            file_url = '/static/downloads/' + os.path.basename(filename)
            progress_dict[task_id]['file_url'] = file_url
            progress_dict[task_id]['status'] = 'finished'
            progress_dict[task_id]['progress'] = 100.0
            
        except Exception as e:
            print(f"Ошибка при скачивании: {str(e)}")
            progress_dict[task_id]['status'] = 'error'
            progress_dict[task_id]['error'] = str(e)

    Thread(target=run_download).start()
    return jsonify({'task_id': task_id})

@app.route('/api/progress')
def get_progress():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in progress_dict:
        return jsonify({'error': 'Некорректный task_id'}), 400
    prog = progress_dict[task_id]
    return jsonify({
        'progress': prog['progress'],
        'status': prog['status'],
        'file_url': prog.get('file_url'),
        'error': prog.get('error')
    })

@app.route('/api/info', methods=['POST'])
def get_video_info():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL не указан'}), 400

        try:
            # Используем pytube для получения информации
            yt = YouTube(url)
            
            # Получаем доступные форматы
            formats = []
            for stream in yt.streams.filter(progressive=True):
                formats.append({
                    'format_id': stream.itag,
                    'ext': stream.mime_type.split('/')[-1],
                    'format_note': f"{stream.resolution} ({stream.mime_type.split('/')[-1]})",
                    'filesize': stream.filesize,
                    'height': int(stream.resolution.replace('p', '')),
                    'width': int(stream.resolution.replace('p', '')) * 16 // 9,
                    'fps': stream.fps,
                })
            
            # Добавляем аудио формат
            audio_stream = yt.streams.filter(only_audio=True).first()
            if audio_stream:
                formats.append({
                    'format_id': audio_stream.itag,
                    'ext': 'mp3',
                    'format_note': 'Audio Only (mp3)',
                    'filesize': audio_stream.filesize,
                    'acodec': 'mp3',
                })

            info = {
                'title': yt.title,
                'thumbnail': yt.thumbnail_url,
                'duration': yt.length,
                'formats': formats,
                'webpage_url': url,
            }
            
            return jsonify(info)
                    
        except Exception as e:
            print(f"Ошибка при получении информации: {str(e)}")
            return jsonify({
                'error': 'Не удалось получить информацию о видео. Проверьте ссылку.'
            }), 400
                
    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")
        return jsonify({'error': f'Произошла ошибка: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 