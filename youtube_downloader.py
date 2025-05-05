import yt_dlp
import sys
import re

def validate_url(url):
    """Проверка корректности URL YouTube."""
    youtube_regex = r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$'
    if not re.match(youtube_regex, url):
        return False
    return True

def get_video_info(url):
    if not validate_url(url):
        print("Ошибка: Неверный формат URL YouTube")
        return

    try:
        # Настройки для yt-dlp
        ydl_opts = {
            'quiet': False,  # Включаем вывод информации
            'no_warnings': False,  # Показываем предупреждения
            'extract_flat': False,  # Отключаем flat извлечение
        }

        # Создаем объект yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("Получение информации о видео...")
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            
            print("\nИнформация о видео:")
            print(f"Название: {info.get('title', 'Н/Д')}")
            print(f"Автор: {info.get('uploader', 'Н/Д')}")
            print(f"Длительность: {info.get('duration', 'Н/Д')} секунд")
            print(f"Количество просмотров: {info.get('view_count', 'Н/Д')}")
            
            # Получаем форматы видео
            formats = info.get('formats', [])
            print(f"\nНайдено форматов: {len(formats)}")
            
            if not formats:
                print("Ошибка: Не удалось получить форматы видео")
                print("Полученная информация:", info.keys())
                return
                
            # Фильтруем и сортируем форматы
            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            print(f"Доступных видеоформатов: {len(video_formats)}")
            
            if not video_formats:
                print("Нет доступных форматов для скачивания")
                print("Все форматы:", formats)
                return
                
            print("\nДоступные форматы:")
            for i, format in enumerate(video_formats, 1):
                resolution = f"{format.get('height', 'Н/Д')}p"
                ext = format.get('ext', 'Н/Д')
                filesize = format.get('filesize', 0) / (1024*1024)  # Convert to MB
                print(f"{i}. Разрешение: {resolution}, "
                      f"Формат: {ext}, "
                      f"Размер: {filesize:.1f} MB")

    except Exception as e:
        print(f"\nПроизошла ошибка: {str(e)}")
        print("\nВозможные решения:")
        print("1. Проверьте подключение к интернету")
        print("2. Убедитесь, что видео доступно в вашем регионе")
        print("3. Попробуйте использовать VPN")
        print("4. Проверьте, что URL видео корректный")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        video_url = input("Введите URL видео YouTube: ")
    
    print("Получение информации о видео...")
    get_video_info(video_url) 