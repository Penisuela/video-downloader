document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const videoInfoDiv = document.getElementById('videoInfo');
    const resultDiv = document.getElementById('result');

    let currentFormats = [];
    let currentUrl = '';
    let currentTitle = '';

    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            videoInfoDiv.innerHTML = '';
            resultDiv.innerHTML = '';
            const videoUrl = document.getElementById('videoUrl').value;
            const submitButton = searchForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Поиск...';
            try {
                const response = await fetch('/api/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: videoUrl })
                });
                const data = await response.json();
                if (response.ok) {
                    currentFormats = data.formats;
                    currentUrl = videoUrl;
                    currentTitle = data.title;
                    renderVideoInfo(data);
                } else {
                    videoInfoDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            } catch (error) {
                videoInfoDiv.innerHTML = `<div class="alert alert-danger">Произошла ошибка при поиске видео</div>`;
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Поиск';
            }
        });
    }

    function renderVideoInfo(data) {
        // Фильтруем только mp4 и сортируем по убыванию разрешения
        const mp4Formats = (data.formats || [])
            .filter(f => f.ext === 'mp4')
            .sort((a, b) => (b.height || 0) - (a.height || 0));
        // Форматируем дату
        let uploadDate = data.upload_date ? (data.upload_date.length === 8 ? `${data.upload_date.slice(6,8)}.${data.upload_date.slice(4,6)}.${data.upload_date.slice(0,4)}` : data.upload_date) : '';
        // Форматируем просмотры и лайки
        let views = data.view_count ? data.view_count.toLocaleString('ru-RU') : '';
        let likes = data.like_count ? data.like_count.toLocaleString('ru-RU') : '';
        let duration = formatDuration(data.duration);
        let channel = data.channel || '';
        let channelId = data.channel_id || '';
        let uploaderId = data.uploader_id || '';
        let channelFollowers = data.channel_follower_count ? data.channel_follower_count.toLocaleString('ru-RU') : '';
        let html = `<div class='row g-3 align-items-center mb-4 video-header-block'>
            <div class='col-md-4 text-center'>
                <img src='${data.thumbnail}' class='img-fluid rounded shadow' alt='thumbnail' style='max-height: 260px;'>
            </div>
            <div class='col-md-8'>
                <h3 class='mb-3'>${data.title}</h3>
                <div class='row'>
                  <div class='col-6 d-flex flex-column gap-2'>
                    <span>👤 ${data.uploader || 'Неизвестно'}</span>
                    ${channelFollowers ? `<span>👥 ${channelFollowers}</span>` : ''}
                    <span>👁️ ${views}</span>
                  </div>
                  <div class='col-6 d-flex flex-column gap-2'>
                    <span>👍 ${likes}</span>
                    <span>⏱️ ${duration}</span>
                    <span>📅 ${uploadDate}</span>
                  </div>
                </div>
            </div>
        </div>`;
        html += `<div class='row row-cols-1 row-cols-sm-2 row-cols-md-4 g-4 custom-g-16'>`;
        mp4Formats.forEach(f => {
            let isYouTube = (data.extractor && data.extractor.toLowerCase().includes('youtube')) || (data.webpage_url && data.webpage_url.includes('youtube.com'));
            let resolution = f.height ? `${f.height}p` : '—';
            let ext = f.ext || '—';
            let vcodec = f.vcodec || '';
            let acodec = f.acodec || '—';
            let filesize;
            if (f.filesize) {
                filesize = (f.filesize / 1024 / 1024).toFixed(1) + ' MB';
            } else if (f.filesize_approx) {
                filesize = (f.filesize_approx / 1024 / 1024).toFixed(1) + ' MB';
            } else if (f.tbr && data.duration) {
                // bitrate (tbr) в Kbps, duration в секундах
                // 1 байт = 8 бит, 1 МБ = 1024*1024 байт
                // tbr (Kbps) * 1024 (в биты) / 8 (в байты) * duration (сек) / 1024 / 1024 (в МБ)
                let estimated_size = (f.tbr * 1024 * data.duration) / (8 * 1024 * 1024);
                filesize = estimated_size.toFixed(1) + ' MB';
            } else {
                filesize = '—';
            }
            let fps = f.fps ? f.fps + ' FPS' : '—';
            let tbr = f.tbr ? Math.round(f.tbr) + ' Kbps' : '—';
            let formatNote = f.format_note ? f.format_note : '';
            let width = f.width ? f.width + 'px' : '';
            html += `<div class='col'>
                <div class='download-block h-100 p-4 d-flex flex-column justify-content-between'>
                    <div>
                        <div class='resolution mb-2'><span class='info-icon'>🎬</span>${resolution}</div>
                        <div class='format-label mb-2'>${ext}${isYouTube && vcodec ? ' (' + vcodec + ')' : ''}${formatNote && !isYouTube ? ' <span style=\"color:#b0b0b0\">(' + formatNote + ')</span>' : ''}</div>
                        <div class='info-row mb-1'><span class='info-icon'>📁</span>${filesize}</div>
                        <div class='info-row mb-1'><span class='info-icon'>🎞️</span>${fps}</div>
                        <div class='info-row mb-1'><span class='info-icon'>📶</span>${tbr}</div>
                        ${!isYouTube && acodec ? `<div class='info-row mb-1'><span class='info-icon'>🎶</span>${acodec}</div>` : ''}
                        ${!isYouTube && vcodec ? `<div class='info-row mb-1'><span class='info-icon'>🎥</span>${vcodec}</div>` : ''}
                        ${!isYouTube && width ? `<div class='info-row mb-1'><span class='info-icon'>📐</span>${width}</div>` : ''}
                    </div>
                    <button class='btn btn-success w-100 mt-3 download-btn' data-format='${f.format_id}'>⬇ Скачать видео</button>
                </div>
            </div>`;
        });
        html += `</div>`;
        html += `<div id='progressBarWrap' class='mt-4' style='display:none;'>
            <div class='progress' style='height: 28px;'>
                <div class='progress-bar progress-bar-striped progress-bar-animated bg-success' role='progressbar' style='width: 0%'>0.00%</div>
            </div>
        </div>`;
        videoInfoDiv.innerHTML = html;
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.onclick = () => startDownload(btn.getAttribute('data-format'));
        });
    }

    function formatDuration(seconds) {
        if (!seconds) return 'Неизвестно';
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    async function startDownload(formatId) {
        resultDiv.innerHTML = '';
        const progressBarWrap = document.getElementById('progressBarWrap');
        const progressBar = progressBarWrap.querySelector('.progress-bar');
        progressBarWrap.style.display = 'block';
        progressBar.style.width = '0%';
        progressBar.innerText = '0.00%';
        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentUrl, format_id: formatId })
            });
            const data = await response.json();
            if (response.ok && data.task_id) {
                await pollProgress(data.task_id);
            } else {
                resultDiv.innerHTML = `<div class="alert alert-danger">${data.error || 'Ошибка при запуске скачивания'}</div>`;
                progressBarWrap.style.display = 'none';
            }
        } catch (error) {
            resultDiv.innerHTML = `<div class="alert alert-danger">Произошла ошибка при скачивании</div>`;
            progressBarWrap.style.display = 'none';
        }
    }

    async function pollProgress(taskId) {
        const progressBar = document.querySelector('.progress-bar');
        const progressBarWrap = document.getElementById('progressBarWrap');
        let lastProgress = 0;
        while (true) {
            await new Promise(r => setTimeout(r, 500));
            const resp = await fetch(`/api/progress?task_id=${taskId}`);
            const data = await resp.json();
            if (data.status === 'error') {
                resultDiv.innerHTML = `<div class="alert alert-danger">${data.error || 'Ошибка при скачивании'}</div>`;
                progressBarWrap.style.display = 'none';
                break;
            }
            let prog = data.progress || 0;
            // Не даём прогрессу откатываться назад
            if (prog < lastProgress) prog = lastProgress;
            lastProgress = prog;
            progressBar.style.width = prog.toFixed(2) + '%';
            progressBar.innerText = prog.toFixed(2) + '%';
            if (data.status === 'finished' && data.file_url) {
                progressBar.style.width = '100%';
                progressBar.innerText = '100.00%';
                // Автоматически скачиваем файл
                const a = document.createElement('a');
                a.href = data.file_url;
                a.download = '';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                resultDiv.innerHTML = `<div class="alert alert-success">Видео успешно скачано!</div>`;
                setTimeout(() => { progressBarWrap.style.display = 'none'; }, 2000);
                break;
            }
        }
    }
}); 