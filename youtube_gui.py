import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                           QScrollArea, QFrame, QProgressBar, QGridLayout, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QRectF, QByteArray, QUrl
from PyQt6.QtGui import QFont, QIcon, QMovie, QPixmap, QPainter, QPen, QColor, QPainterPath
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
import yt_dlp
import re
from youtube_downloader import validate_url
import json
import urllib.request
import requests

def load_svg_with_color(path, size, color="white"):
    try:
        # Проверяем существование файла
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return None

        # Читаем SVG файл
        with open(path, 'r') as file:
            svg_content = file.read()
        
        # Заменяем цвет в SVG
        if 'fill="' in svg_content:
            svg_content = re.sub('fill="[^"]*"', f'fill="{color}"', svg_content)
        else:
            svg_content = svg_content.replace('<svg', f'<svg fill="{color}"')
        
        # Создаем рендерер и pixmap
        renderer = QSvgRenderer()
        if not renderer.load(bytes(svg_content, encoding='utf-8')):
            print(f"Failed to load SVG content for {path}")
            return None
        
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Рисуем SVG на pixmap
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return pixmap
    except Exception as e:
        print(f"Error loading SVG {path}: {str(e)}")
        return None

class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(24, 24)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen()
        pen.setWidth(2)
        pen.setColor(QColor("#FFFFFF"))
        painter.setPen(pen)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # Рисуем дугу по часовой стрелке
        painter.drawArc(rect, (90 - self.angle) * 16, -300 * 16)

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def start(self):
        self.show()
        self.timer.start(30)

    def stop(self):
        self.timer.stop()
        self.hide()

class SearchButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("Поиск", parent)
        self.setFixedWidth(100)
        
        # Создаем спиннер
        self.spinner = LoadingSpinner(self)
        self.spinner.hide()
        
        # Центрируем спиннер на кнопке
        self.updateSpinnerPosition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateSpinnerPosition()

    def updateSpinnerPosition(self):
        # Центрируем спиннер на кнопке
        x = (self.width() - self.spinner.width()) // 2
        y = (self.height() - self.spinner.height()) // 2
        self.spinner.move(x, y)

    def startLoading(self):
        self.setText("")  # Убираем текст
        self.spinner.start()

    def stopLoading(self):
        self.spinner.stop()
        self.setText("Поиск")

def resolve_tiktok_url(url):
    """Получает настоящий URL из короткой ссылки TikTok"""
    try:
        response = requests.head(url, allow_redirects=True)
        return response.url
    except Exception as e:
        print(f"Ошибка при разрешении короткой ссылки: {str(e)}")
        return url

def clean_tiktok_url(url):
    """Очищает URL TikTok от лишних параметров"""
    # Если это короткая ссылка, пробуем получить полный URL
    if 'vt.tiktok.com' in url:
        url = resolve_tiktok_url(url)
        
    # Ищем базовый путь для фото или видео
    photo_match = re.search(r'(https?://(?:www\.)?tiktok\.com/@[^/]+/photo/\d+)', url)
    video_match = re.search(r'(https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+)', url)
    username_match = re.search(r'(https?://(?:www\.)?tiktok\.com/@[^/\?]+)', url)
    
    if photo_match:
        return photo_match.group(1)
    elif video_match:
        return video_match.group(1)
    elif username_match:
        return username_match.group(1)
    
    return url

def validate_url(url):
    """Проверка URL на соответствие YouTube, TikTok или Instagram"""
    youtube_pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+(\S*)?$'
    tiktok_pattern = r'^(https?://)?((?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+)$'
    instagram_pattern = r'^(https?://)?((?:www\.)?instagram\.com/(?:p|reel|tv|reels|stories)/[a-zA-Z0-9_-]+(?:/\?.*)?|instagram\.com/[^/]+/[^/]+)$'
    
    return bool(re.match(youtube_pattern, url) or 
                re.match(tiktok_pattern, url) or 
                re.match(instagram_pattern, url))

def get_tiktok_photo_info(url):
    """Получает информацию о фото TikTok"""
    try:
        # Извлекаем username и photo_id из URL
        match = re.search(r'@([^/]+)/photo/(\d+)', url)
        if not match:
            raise Exception("Неверный формат URL фотографии")
            
        username, photo_id = match.groups()
        
        # Создаем базовую информацию о фото
        return {
            'title': f'Photo by @{username}',
            'uploader': username,
            'id': photo_id,
            'webpage_url': url,
            'extractor': 'TikTok',
            'extractor_key': 'TikTok',
            '_type': 'photo',
            'thumbnails': [{
                'url': url,
                'id': 'photo'
            }]
        }
    except Exception as e:
        raise Exception(f"Ошибка при получении информации о фото: {str(e)}")

class SearchThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # Очищаем URL если это TikTok
            if 'tiktok.com' in self.url:
                cleaned_url = clean_tiktok_url(self.url)
                print(f"Оригинальный URL: {self.url}")
                print(f"Очищенный URL: {cleaned_url}")
                self.url = cleaned_url
                
                # Проверяем, является ли это фотографией
                if '/photo/' in self.url:
                    info = get_tiktok_photo_info(self.url)
                    self.finished.emit(info)
                    return
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,
            }
            
            # Для TikTok и Instagram добавляем специальные опции
            if 'tiktok.com' in self.url or 'instagram.com' in self.url:
                ydl_opts.update({
                    'format': 'best',  # Выбираем лучшее качество
                    'extract_flat': True,  # Быстрое извлечение информации
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self.finished.emit(info)
        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка при загрузке: {error_msg}")
            self.error.emit(error_msg)

    def update_info(self, info):
        """Обновить информацию о видео"""
        if not info:
            return
            
        self.title.setText(info.get('title', 'Название неизвестно'))
        
        # Форматируем числа
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Обновляем информацию
        self.author_label.setText(f"👤 {info.get('uploader', 'Неизвестно')}")
        self.views_label.setText(f"👁️ {format_number(info.get('view_count', 0))}")
        
        # Определяем, является ли это TikTok видео
        is_tiktok = 'tiktok.com' in info.get('webpage_url', '').lower()
        
        if is_tiktok:
            # Для TikTok показываем название трека
            track = info.get('track', '')
            if track:
                self.subscribers_label.setText(f"🎵 {track}")
            else:
                self.subscribers_label.setText("🎵 Оригинальный звук")
        else:
            # Для YouTube показываем подписчиков
            self.subscribers_label.setText(f"👥 {format_number(info.get('channel_follower_count', 0))}")
        
        self.likes_label.setText(f"👍 {format_number(info.get('like_count', 0))}")
        
        # Форматируем длительность видео
        duration = info.get('duration', 0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}:{seconds:02d}"
        self.duration_label.setText(f"⏱️ {duration_str}")
        
        # Форматируем дату
        upload_date = info.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            year = upload_date[:4]
            month = upload_date[4:6]
            day = upload_date[6:]
            self.date_label.setText(f"📅 {day}.{month}.{year}")
        else:
            self.date_label.setText("📅 Дата неизвестна")
        
        # Загружаем превью
        if is_tiktok:
            # Для TikTok используем thumbnail из информации
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                # Берем последний thumbnail (обычно лучшего качества)
                thumbnail_url = thumbnails[-1].get('url')
                if thumbnail_url:
                    if self.thumbnail_loader is not None:
                        self.thumbnail_loader.quit()
                    self.thumbnail_loader = ThumbnailLoader(thumbnail_url)
                    self.thumbnail_loader.thumbnail_loaded.connect(self.set_thumbnail)
                    self.thumbnail_loader.start()
        else:
            # Для YouTube используем стандартную логику
            if 'id' in info:
                video_id = info['id']
                # Пробуем разные размеры превью
                thumbnail_urls = [
                    f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
                ]
                
                if self.thumbnail_loader is not None:
                    self.thumbnail_loader.quit()
                self.thumbnail_loader = ThumbnailLoader(thumbnail_urls[0])  # Начинаем с maxresdefault
                self.thumbnail_loader.thumbnail_loaded.connect(self.set_thumbnail)
                self.thumbnail_loader.start()

class DownloadThread(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, format_id, output_path):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.is_cancelled = False

    def run(self):
        try:
            ydl_opts = {
                'format': f'{self.format_id}+bestaudio[ext=m4a]/best',
                'outtmpl': self.output_path,
                'merge_output_format': 'mp4',
                'postprocessor_args': ['-c', 'copy'],
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [self.progress_hook]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if not self.is_cancelled:  # Проверяем перед началом загрузки
                    ydl.download([self.url])
                    if not self.is_cancelled:  # Проверяем после загрузки
                        self.finished.emit()
        except Exception as e:
            if not self.is_cancelled:  # Отправляем ошибку только если не было отмены
                self.error.emit(str(e))

    def progress_hook(self, d):
        if self.is_cancelled:  # Проверяем отмену перед обновлением прогресса
            return
            
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                progress = (downloaded_bytes / total_bytes) * 100
                # Ограничиваем прогресс до 100%
                progress = min(progress, 100)
                self.progress.emit(progress / 100)
        
        elif d['status'] == 'finished':
            self.progress.emit(1.0)

    def cancel(self):
        self.is_cancelled = True
        self.terminate()
        self.wait()

def sanitize_filename(filename):
    # Заменяем недопустимые символы на безопасные
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Ограничиваем длину имени файла
    return filename[:200]  # Оставляем место для расширения

class VideoInfoWidget(QFrame):
    def __init__(self, format_info, parent=None):
        super().__init__(parent)
        self.format_info = format_info
        self.setup_ui()

    def setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(240, 240)  # Размер карточки
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 12px;
                padding: 20px 24px;
                margin: 0px;
            }
            QLabel {
                color: #FFFFFF;
                padding: 0px;
                margin: 0px;
            }
            QLabel.title {
                color: white;
                font-size: 20px;
                font-weight: 600;
            }
            QLabel.format {
                color: #999999;
                font-size: 13px;
                font-weight: 400;
            }
            QLabel.info {
                color: #CCCCCC;
                font-size: 14px;
                font-weight: 400;
            }
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 0;
                margin-top: 18px;
            }
            QPushButton:hover {
                background-color: #17a74a;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(4)  # Уменьшенный отступ между элементами
        main_layout.setContentsMargins(24, 20, 24, 20)  # Отступы как в дизайне
        
        # Заголовок с разрешением
        height = self.format_info.get('height', '?')
        resolution_text = f"{height}p"
        title_label = QLabel("🎥 " + resolution_text)
        title_label.setProperty("class", "title")

        # Размер файла
        filesize = self.format_info.get('filesize', 0)
        filesize_approx = self.format_info.get('filesize_approx', 0)
        tbr = self.format_info.get('tbr', 0)
        duration = self.format_info.get('duration', 0)
        
        if filesize > 0:
            size_text = f"📁 {filesize / (1024*1024):.1f} MB"
        elif filesize_approx > 0:
            size_text = f"📁 {filesize_approx / (1024*1024):.1f} MB"
        elif tbr > 0 and duration > 0:
            # Если есть битрейт и длительность, можем оценить размер
            estimated_size = (tbr * 1024 * duration) / (8 * 1024)  # Конвертируем в МБ
            size_text = f"📁 {estimated_size:.1f} MB"
        else:
            size_text = "📁 Размер неизвестен"
        size_label = QLabel(size_text)
        size_label.setProperty("class", "info")
        
        # Размеры видео
        width = self.format_info.get('width', 0)
        height = self.format_info.get('height', 0)
        if width and height:
            dimensions_text = f"📐 {width}x{height}"
        else:
            dimensions_text = "📐 Размер неизвестен"
        dimensions_label = QLabel(dimensions_text)
        dimensions_label.setProperty("class", "info")
        
        # Аудиокодек
        acodec = self.format_info.get('acodec', 'none')
        if acodec != 'none':
            if acodec == 'mp4a.40.2':
                acodec = 'AAC'
            elif acodec == 'opus':
                acodec = 'Opus'
            audio_text = f"🔊 {acodec}"
        else:
            audio_text = "🔇 Без звука"
        audio_label = QLabel(audio_text)
        audio_label.setProperty("class", "info")
        
        # Добавляем элементы в layout
        main_layout.addWidget(title_label)
        main_layout.addSpacing(12)  # Отступ перед информационными строками
        main_layout.addWidget(size_label)
        main_layout.addWidget(dimensions_label)
        main_layout.addWidget(audio_label)
        main_layout.addStretch()
        
        # Кнопка скачивания
        download_btn = QPushButton("⬇ Скачать видео")
        download_btn.clicked.connect(self.start_download)
        main_layout.addWidget(download_btn)
        
        self.setLayout(main_layout)

    def start_download(self):
        main_window = None
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, MainWindow):  # Changed from YouTubeDownloader to MainWindow
                main_window = parent
                break
            parent = parent.parent()
        
        if main_window:
            main_window.start_download(self.format_info)

class ThumbnailLoader(QThread):
    thumbnail_loaded = pyqtSignal(QPixmap)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            # Создаем временный файл для превью
            temp_path = "temp_thumbnail.jpg"
            
            # Скачиваем превью
            urllib.request.urlretrieve(self.url, temp_path)
            
            # Загружаем в QPixmap
            pixmap = QPixmap(temp_path)
            if not pixmap.isNull():
                self.thumbnail_loaded.emit(pixmap)
            
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            print(f"Ошибка загрузки превью: {str(e)}")

class VideoInfoHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnail_loader = None
        self.setup_ui()
        
    def setup_ui(self):
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 0, 0, 0)  # Отступы: левый 20px, верхний и нижний 16px, правый 0px
        main_layout.setSpacing(20)
        
        # Создаем карточку для всей информации
        info_card = QFrame()
        info_card.setFixedSize(930, 210)
        info_card.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                background: transparent;
            }
            QLabel.title {
                font-size: 20px;
                font-weight: 600;
            }
        """)
        
        card_layout = QVBoxLayout(info_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        
        # Превью и информация
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # Превью
        preview_container = QFrame()
        preview_container.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border-radius: 8px;
            }
        """)
        preview_container.setFixedSize(303, 170)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        
        self.preview = QLabel()
        self.preview.setFixedSize(303, 170)
        self.preview.setScaledContents(True)
        preview_layout.addWidget(self.preview)
        
        top_layout.addWidget(preview_container)
        
        # Информация справа от превью
        info_layout = QVBoxLayout()
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(20, 0, 0, 0)  # Отступ только слева
        
        # Название
        self.title = QLabel("Название видео")
        self.title.setProperty("class", "title")
        self.title.setWordWrap(True)
        info_layout.addWidget(self.title)
        
        # Сетка с информацией
        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)
        grid_layout.setVerticalSpacing(8)
        
        # Левая колонка
        self.author_label = QLabel("👤 Автор")
        self.views_label = QLabel("👁️ Просмотров")
        self.subscribers_label = QLabel("👥 Подписчиков")
        
        grid_layout.addWidget(self.author_label, 0, 0)
        grid_layout.addWidget(self.views_label, 1, 0)
        grid_layout.addWidget(self.subscribers_label, 2, 0)
        
        # Правая колонка
        self.likes_label = QLabel("👍 Лайков")
        self.duration_label = QLabel("⏱️ Длительность")
        self.date_label = QLabel("📅 Дата публикации")
        
        grid_layout.addWidget(self.likes_label, 0, 2)
        grid_layout.addWidget(self.duration_label, 1, 2)
        grid_layout.addWidget(self.date_label, 2, 2)
        
        # Добавляем распорки между колонками
        grid_layout.setColumnMinimumWidth(1, 100)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)
        
        # Добавляем растягивающийся виджет сверху
        spacer_top = QWidget()
        spacer_top.setFixedHeight(0)
        info_layout.insertWidget(0, spacer_top)
        info_layout.setStretch(0, 1)  # Растягиваем верхний спейсер
        
        info_layout.addLayout(grid_layout)
        
        # Добавляем растягивающийся виджет снизу
        spacer_bottom = QWidget()
        spacer_bottom.setFixedHeight(0)
        info_layout.addWidget(spacer_bottom)
        info_layout.setStretch(4, 1)  # Растягиваем нижний спейсер
        
        top_layout.addLayout(info_layout)
        card_layout.addLayout(top_layout)
        
        main_layout.addWidget(info_card)
    
    def update_info(self, info):
        """Обновить информацию о видео"""
        if not info:
            return
            
        self.title.setText(info.get('title', 'Название неизвестно'))
        
        # Форматируем числа
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Обновляем информацию
        self.author_label.setText(f"👤 {info.get('uploader', 'Неизвестно')}")
        self.views_label.setText(f"👁️ {format_number(info.get('view_count', 0))}")
        
        # Определяем, является ли это TikTok видео
        is_tiktok = 'tiktok.com' in info.get('webpage_url', '').lower()
        
        if is_tiktok:
            # Для TikTok показываем размеры видео
            width = info.get('width', 0)
            height = info.get('height', 0)
            if width and height:
                dimensions_text = f"📐 {width}x{height}"
            else:
                dimensions_text = "📐 Размер неизвестен"
            dimensions_label = QLabel(dimensions_text)
            dimensions_label.setProperty("class", "info")
        else:
            # Для YouTube показываем FPS
            fps = info.get('fps', 0)
            fps_text = f"🎞️ {fps} FPS" if fps else "🎞️ FPS неизвестно"
            dimensions_label = QLabel(fps_text)
            dimensions_label.setProperty("class", "info")
        
        self.likes_label.setText(f"👍 {format_number(info.get('like_count', 0))}")
        
        # Форматируем длительность видео
        duration = info.get('duration', 0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}:{seconds:02d}"
        self.duration_label.setText(f"⏱️ {duration_str}")
        
        # Форматируем дату
        upload_date = info.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            year = upload_date[:4]
            month = upload_date[4:6]
            day = upload_date[6:]
            self.date_label.setText(f"📅 {day}.{month}.{year}")
        else:
            self.date_label.setText("📅 Дата неизвестна")
        
        # Загружаем превью
        if is_tiktok:
            # Для TikTok используем thumbnail из информации
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                # Берем последний thumbnail (обычно лучшего качества)
                thumbnail_url = thumbnails[-1].get('url')
                if thumbnail_url:
                    if self.thumbnail_loader is not None:
                        self.thumbnail_loader.quit()
                    self.thumbnail_loader = ThumbnailLoader(thumbnail_url)
                    self.thumbnail_loader.thumbnail_loaded.connect(self.set_thumbnail)
                    self.thumbnail_loader.start()
        else:
            # Для YouTube используем стандартную логику
            if 'id' in info:
                video_id = info['id']
                # Пробуем разные размеры превью
                thumbnail_urls = [
                    f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
                ]
                
                if self.thumbnail_loader is not None:
                    self.thumbnail_loader.quit()
                self.thumbnail_loader = ThumbnailLoader(thumbnail_urls[0])  # Начинаем с maxresdefault
                self.thumbnail_loader.thumbnail_loaded.connect(self.set_thumbnail)
                self.thumbnail_loader.start()
    
    def set_thumbnail(self, pixmap):
        """Установить загруженное превью"""
        if not pixmap.isNull():
            # Создаем новый pixmap с закругленными углами
            rounded_pixmap = QPixmap(self.preview.size())
            rounded_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Создаем путь с закругленными углами
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.preview.width(), self.preview.height(), 8, 8)
            
            # Отрисовываем изображение с маской
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            ))
            painter.end()
            
            self.preview.setPixmap(rounded_pixmap)
            print("\nПревью успешно установлено")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Downloader")  # Обновляем название окна
        self.setWindowIcon(QIcon("assets/icons/icon.ico"))
        self.setMinimumSize(1000, 800)
        self.setFixedWidth(1000)  # Фиксируем ширину окна
        
        # Инициализация переменных
        self.current_url = ""
        self.search_thread = None
        self.download_thread = None
        self.current_video_info = None
        
        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Верхняя панель с полем ввода и кнопкой
        top_panel = QHBoxLayout()
        top_panel.setContentsMargins(20, 0, 0, 0)
        top_panel.setSpacing(16)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL видео с YouTube, TikTok или Instagram")
        self.url_input.returnPressed.connect(self.search_video)
        
        self.search_button = SearchButton()
        self.search_button.clicked.connect(self.search_video)
        self.search_button.setFixedWidth(120)
        
        top_panel.addWidget(self.url_input)
        top_panel.addWidget(self.search_button)
        
        # Добавляем шапку с информацией о видео
        self.video_info_header = VideoInfoHeader()
        self.video_info_header.hide()  # Скрываем до первого поиска
        
        # Область для информации о видео
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QGridLayout(self.content_widget)
        self.content_layout.setSpacing(16)
        self.content_layout.setContentsMargins(20, 0, 20, 20)
        self.scroll_area.setWidget(self.content_widget)
        
        # Добавляем все в основной layout
        main_layout.addLayout(top_panel)
        main_layout.addWidget(self.video_info_header)
        main_layout.addWidget(self.scroll_area, 1)
        
        # Статус бар для отображения прогресса
        self.setupStatusBar()
        
        # Применяем стили
        self.apply_styles()
        
        # Показываем начальное сообщение
        self.showStatusMessage("Готово к работе")

    def setupStatusBar(self):
        """Настройка статус бара"""
        self.statusBar().setFixedHeight(50)
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #2A2A2A;
                color: #FFFFFF;
                padding: 0;
                margin: 0;
            }
            QStatusBar::item {
                border: none;
                padding: 0;
                margin: 0;
                border-spacing: 0;
            }
            QPushButton {
                height: 35px;
                min-height: 35px;
                max-height: 35px;
            }
        """)

        # Создаем виджет для статус бара
        self.status_widget = QWidget()
        self.status_layout = QHBoxLayout(self.status_widget)
        self.status_layout.setContentsMargins(0, 0, 20, 0)  # Только правый отступ
        self.status_layout.setSpacing(16)  # Расстояние между прогресс баром и кнопкой

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximum(10000)
        self.progress_bar.hide()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #404040;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: white;
                font-size: 13px;
                margin: 0;
                padding: 0;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 4px;
            }
        """)

        # Кнопка отмены
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setFixedSize(120, 30)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid white;
                border-radius: 4px;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_download)

        # Добавляем элементы в layout
        self.status_layout.addWidget(self.progress_bar, 1)
        self.status_layout.addWidget(self.cancel_button)

        # Добавляем в статус бар
        self.statusBar().addPermanentWidget(self.status_widget, 1)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #323232;
            }
            QWidget {
                color: #FFFFFF;
                font-family: Arial;
            }
            QLineEdit {
                padding: 8px 16px 8px 10px;  /* top right bottom left */
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #2A2A2A;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #1DB954;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
            QPushButton:disabled {
                background-color: #404040;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
                background-color: #2A2A2A;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background-color: #323232;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def search_video(self):
        url = self.url_input.text().strip()
        if not url:
            error_label = QLabel("Вставьте URL видео с YouTube, TikTok или Instagram")
            error_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 16px;
                }
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            for i in reversed(range(self.content_layout.count())): 
                widget = self.content_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            self.content_layout.addWidget(error_label, 0, 0, 1, 4, Qt.AlignmentFlag.AlignCenter)
            return
            
        if not validate_url(url):
            error_label = QLabel("Неверный формат URL. Поддерживаются YouTube, TikTok и Instagram.")
            error_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 16px;
                }
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            for i in reversed(range(self.content_layout.count())): 
                widget = self.content_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            self.content_layout.addWidget(error_label, 0, 0, 1, 4, Qt.AlignmentFlag.AlignCenter)
            return

        self.current_url = url
        self.disable_interface()
        self.search_button.startLoading()
        self.showStatusMessage("Поиск видео...")
        
        # Очищаем предыдущие результаты
        for i in reversed(range(self.content_layout.count())): 
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.search_thread = SearchThread(url)
        self.search_thread.finished.connect(self.on_search_complete)
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_complete(self, info):
        self.current_video_info = info
        self.search_button.stopLoading()
        self.enable_interface()
        
        # Обновляем информацию в шапке
        self.video_info_header.update_info(info)
        self.video_info_header.show()
        
        print("\nПревью (thumbnails):")
        if 'thumbnails' in info:
            print(json.dumps(info['thumbnails'], indent=2, ensure_ascii=False))
        else:
            print("Информация о превью отсутствует")

        print("\nВся информация о видео:")
        print(json.dumps(info, indent=2, ensure_ascii=False))
        
        # Фильтруем и сортируем форматы
        formats = []
        for f in info.get('formats', []):
            if f.get('ext') == 'mp4' and f.get('vcodec') and f.get('vcodec') != 'none':
                formats.append(f)
        
        formats.sort(key=lambda x: (
            -int(x.get('quality', 0) or 0),
            -float(x.get('tbr', 0) or 0),
            -(int(x.get('filesize', 0) or 0) if x.get('filesize') is not None else 0),
            -(int(x.get('filesize_approx', 0) or 0) if x.get('filesize_approx') is not None else 0)
        ))
        
        if not formats:
            QMessageBox.warning(self, "Внимание", "Не найдено подходящих MP4 форматов для скачивания")
            self.showStatusMessage("Готово для работы")
            return
            
        # Создаем карточки форматов в сетке 4 столбца
        row = 0
        col = 0
        for fmt in formats:
            format_card = self.create_format_card(fmt)
            self.content_layout.addWidget(format_card, row, col)
            col += 1
            if col >= 4:  # Переходим на новую строку после 4 карточек
                col = 0
                row += 1
            
        self.showStatusMessage(f"Найдено {len(formats)} форматов")

    def create_format_card(self, fmt):
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setFixedSize(220, 208)
        card.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                padding: 0;
                margin: 0;
            }
            QLabel {
                color: #FFFFFF;
                padding: 0;
                margin: 0;
                line-height: 1;
            }
            QLabel.title {
                color: white;
                font-size: 24px;
                font-weight: 600;
            }
            QLabel.subtitle {
                color: #999999;
                font-size: 14px;
                font-weight: 400;
            }
            QLabel.info {
                color: #CCCCCC;
                font-size: 14px;
                font-weight: 400;
            }
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0;
                margin: 0;
                height: 35px;
                min-height: 35px;
                max-height: 35px;
            }
            QPushButton:hover {
                background-color: #17a74a;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Контейнер для информации
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(0)  # Убираем отступ между элементами
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок с разрешением
        height = fmt.get('height', 0)
        resolution = f"{height}p" if height else "?"
        title_label = QLabel(f"🎥 {resolution}")
        title_label.setProperty("class", "title")
        
        # Формат и кодек как подзаголовок
        vcodec = fmt.get('vcodec', 'unknown').split('.')[0]
        if vcodec == 'avc1':
            vcodec = 'h264'
        elif vcodec == 'vp09':
            vcodec = 'vp09'
        format_text = f"MP4 ({vcodec})"
        format_label = QLabel(format_text)
        format_label.setProperty("class", "subtitle")
        
        # Добавляем заголовок и подзаголовок
        info_layout.addWidget(title_label)
        info_layout.addSpacing(1)  # Отступ между разрешением и форматом
        info_layout.addWidget(format_label)
        info_layout.addSpacing(4)  # Отступ перед метриками
        
        # Контейнер для метрик (размер, FPS, битрейт)
        metrics_container = QWidget()
        metrics_layout = QVBoxLayout(metrics_container)
        metrics_layout.setSpacing(1)  # Отступ между метриками как на картинке
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        
        # Размер файла
        filesize = fmt.get('filesize')
        filesize_approx = fmt.get('filesize_approx')
        if filesize is not None and filesize > 0:
            size_text = f"📁 {filesize / (1024*1024):.1f} MB"
        elif filesize_approx is not None and filesize_approx > 0:
            size_text = f"📁 {filesize_approx / (1024*1024):.1f} MB"
        else:
            tbr = fmt.get('tbr', 0)
            duration = self.current_video_info.get('duration', 0)
            if tbr > 0 and duration > 0:
                compression_factor = 0.5
                estimated_size = (tbr * 1024 * duration * compression_factor) / (8 * 1024 * 1024)
                size_text = f"📁 {estimated_size:.1f} MB"
            else:
                size_text = "📁 Размер неизвестен"
        size_label = QLabel(size_text)
        size_label.setProperty("class", "info")
        
        # Определяем тип видео
        webpage_url = self.current_video_info.get('webpage_url', '').lower()
        is_tiktok = 'tiktok.com' in webpage_url
        is_instagram = 'instagram.com' in webpage_url
        
        if is_tiktok or is_instagram:
            # Для TikTok и Instagram показываем размеры видео
            width = fmt.get('width', 0)
            height = fmt.get('height', 0)
            if width and height:
                dimensions_text = f"📐 {width}x{height}"
            else:
                dimensions_text = "📐 Размер неизвестен"
            dimensions_label = QLabel(dimensions_text)
            dimensions_label.setProperty("class", "info")
        else:
            # Для YouTube показываем FPS
            fps = fmt.get('fps', 0)
            fps_text = f"🎞️ {fps} FPS" if fps else "🎞️ FPS неизвестно"
            dimensions_label = QLabel(fps_text)
            dimensions_label.setProperty("class", "info")
        
        # Битрейт (меняем иконку на 📶)
        tbr = fmt.get('tbr', 0)
        if tbr > 0:
            bitrate_text = f"📶 {tbr:.0f} Kbps"
        else:
            bitrate_text = "📶 Битрейт неизвестен"
        bitrate_label = QLabel(bitrate_text)
        bitrate_label.setProperty("class", "info")
        
        # Добавляем метрики
        metrics_layout.addWidget(size_label)
        metrics_layout.addWidget(dimensions_label)
        metrics_layout.addWidget(bitrate_label)
        
        # Добавляем контейнер с метриками
        info_layout.addWidget(metrics_container)
        info_layout.addStretch()
        
        # Добавляем информационный контейнер в главный layout
        main_layout.addWidget(info_container)
        
        # Кнопка скачивания
        download_btn = QPushButton("⬇ Скачать видео")
        download_btn.setFixedHeight(35)
        download_btn.clicked.connect(lambda: self.start_download(fmt))
        main_layout.addWidget(download_btn)
        
        card.setLayout(main_layout)
        return card

    def start_download(self, fmt):
        if not self.current_video_info:
            return
            
        # Создаем безопасное имя файла
        title = self.current_video_info.get('title', 'video')
        safe_title = sanitize_filename(title)
        
        # Открываем диалог выбора места сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить видео",
            os.path.join(os.path.expanduser('~'), 'Desktop', f"{safe_title}.mp4"),
            "MP4 Files (*.mp4)"
        )
        
        if not file_path:
            return
            
        self.disable_interface()
        # Сбрасываем прогресс бар
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.cancel_button.hide()
        self.showStatusMessage("Подготовка...")
        
        self.download_thread = DownloadThread(
            self.current_url,
            fmt['format_id'],
            file_path
        )
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.on_download_complete)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def update_progress(self, progress):
        """Обновить прогресс загрузки"""
        if self.download_thread.is_cancelled:  # Проверяем отмену
            return
            
        # При первом обновлении прогресса показываем элементы загрузки
        if not self.progress_bar.isVisible():
            self.showStatusMessage("Загрузка видео...")
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.cancel_button.show()
            self.status_widget.show()

        # Обновляем значение прогресса (progress приходит как число от 0 до 1)
        current_value = self.progress_bar.value()
        new_value = int(progress * 10000)
        
        # Обновляем только если новое значение больше текущего
        if new_value > current_value:
            self.progress_bar.setValue(new_value)
            self.progress_bar.setFormat(f"{progress * 100:.2f}%")

    def on_download_complete(self):
        self.progress_bar.hide()
        self.cancel_button.hide()
        self.enable_interface()
        self.showStatusMessage("Видео скачано")

    def on_search_error(self, error_msg):
        self.search_button.stopLoading()
        self.enable_interface()
        # Создаем и показываем сообщение об ошибке по центру
        error_label = QLabel("Видео не найдено")
        error_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
            }
        """)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Добавляем метку в центр content_layout
        self.content_layout.addWidget(error_label, 0, 0, 1, 4, Qt.AlignmentFlag.AlignCenter)

    def on_download_error(self, error_msg):
        self.progress_bar.hide()
        self.cancel_button.hide()
        self.enable_interface()
        self.showStatusMessage("Ошибка при загрузке")
        QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить видео:\n{error_msg}")

    def disable_interface(self):
        self.url_input.setEnabled(False)
        self.search_button.setEnabled(False)
        
        # Отключаем все кнопки загрузки
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if isinstance(widget, QFrame):
                for child in widget.findChildren(QPushButton):
                    child.setEnabled(False)

    def enable_interface(self):
        self.url_input.setEnabled(True)
        self.search_button.setEnabled(True)
        
        # Включаем все кнопки загрузки
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if isinstance(widget, QFrame):
                for child in widget.findChildren(QPushButton):
                    child.setEnabled(True)

    def cancel_download(self):
        """Отмена загрузки"""
        if self.download_thread and self.download_thread.isRunning():
            # Блокируем кнопку отмены
            self.cancel_button.setEnabled(False)
            
            # Отменяем загрузку
            self.download_thread.cancel()
            
            # Очищаем интерфейс
            self.progress_bar.setValue(0)
            self.progress_bar.hide()
            self.cancel_button.hide()
            self.enable_interface()
            self.showStatusMessage("Загрузка отменена")
            
            # Восстанавливаем кнопку отмены
            self.cancel_button.setEnabled(True)

    def showStatusMessage(self, message):
        """Показать сообщение в статус баре"""
        # Очищаем все предыдущие сообщения
        self.statusBar().clearMessage()
        for child in self.statusBar().findChildren(QLabel):
            if child is not self.status_widget:
                child.deleteLater()

        # Создаем лейбл для сообщения
        label = QLabel(message)
        label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                margin: 0;
                padding: 0;
                background: transparent;
            }
        """)
        label.setContentsMargins(20, 0, 0, 0)

        # Добавляем в статус бар
        self.statusBar().addWidget(label)

        # Если есть видимый прогресс бар, добавляем разделитель
        if self.progress_bar.isVisible():
            spacer = QWidget()
            spacer.setFixedWidth(16)
            spacer.setStyleSheet("background: transparent; margin: 0; padding: 0; border: none;")
            self.statusBar().addWidget(spacer)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())