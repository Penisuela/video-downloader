from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os
import yt_dlp
import re
import uuid
from flask import send_file
from threading import Thread
from time import sleep

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
    return bool(re.match(youtube_pattern, url))

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
            outtmpl = os.path.join(save_path, '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': format_id if format_id else 'best',
                'outtmpl': outtmpl,
                'quiet': False,
                'no_warnings': False,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'extract_flat': False,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Начинаем скачивание: {url}")
                info = ydl.extract_info(url)
                if info:
                    filename = ydl.prepare_filename(info)
                    file_url = '/static/downloads/' + os.path.basename(filename)
                    progress_dict[task_id]['file_url'] = file_url
                    progress_dict[task_id]['status'] = 'finished'
                    progress_dict[task_id]['progress'] = 100.0
                    print(f"Скачивание завершено: {filename}")
                else:
                    progress_dict[task_id]['status'] = 'error'
                    progress_dict[task_id]['error'] = 'Не удалось скачать видео'
                    print("Ошибка: информация о видео не получена")
                    
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

        print(f"Получение информации о видео... URL: {url}")
        
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'format': 'best',
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("Начинаем извлечение информации...")
                info = ydl.extract_info(url, download=False)
                if not info:
                    print("Информация не получена")
                    return jsonify({
                        'error': 'Не удалось получить информацию о видео'
                    }), 400
                
                print(f"Получена информация: {info.get('title')}")
                
                # Получаем доступные форматы
                formats = []
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('ext') in ['mp4', 'webm', 'm4a', 'mp3']:
                            formats.append({
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'format_note': f.get('format_note'),
                                'filesize': f.get('filesize'),
                                'filesize_approx': f.get('filesize_approx'),
                                'height': f.get('height'),
                                'width': f.get('width'),
                                'tbr': f.get('tbr'),
                                'acodec': f.get('acodec'),
                                'vcodec': f.get('vcodec'),
                                'fps': f.get('fps'),
                            })
                info['formats'] = formats
                return jsonify(info)
                    
        except Exception as e:
            print(f"Ошибка при получении информации: {str(e)}")
            print(f"Тип ошибки: {type(e)}")
            return jsonify({
                'error': f'Не удалось получить информацию о видео: {str(e)}'
            }), 400
                
    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")
        return jsonify({'error': f'Произошла ошибка: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 