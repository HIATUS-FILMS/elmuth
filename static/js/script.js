let activeMediaTitle = '';

function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
        
        document.getElementById('time').textContent = `${hours}:${minutes}:${seconds}:${milliseconds}`;
        requestAnimationFrame(updateClock);
    }
    
    requestAnimationFrame(updateClock);

    var video = document.getElementById('videoPlayer');
        
        if (Hls.isSupported()) {
            var hls = new Hls();
            hls.loadSource('http://127.0.0.1:8787/public/1/live/master.m3u8');
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                video.play();
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = 'http://127.0.0.1:8787/public/1/live/master.m3u8';
            video.addEventListener('loadedmetadata', function() {
                video.play();
            });
        }

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function formatElapsed(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function progress(elapsed, duration) {
    const prog = Math.max(0, (elapsed / duration) * 100);
    return prog + '%';
}

function updateDashboardState() {
    fetch('/dashboard/status')
        .then(response => response.json())
        .then(data => {
            if (data && data.media && data.media.title) {
                document.getElementById('media-title').innerText = data.media.title;
                activeMediaTitle = data.media.title;
            }
            
            if (data && data.media && data.media.duration) {
                const formattedDuration = formatDuration(data.media.duration);
                document.getElementById('media-duration').innerText = formattedDuration + ' • Ready';
            }

            if (data && data.elapsed !== undefined && data.media && data.media.duration) {
                const formattedElapsed = formatElapsed(data.elapsed);
                document.getElementById('media-elapsed').innerText = 'Time elapsed : ' + formattedElapsed;

                const remainingSeconds = Math.max(0, data.media.duration - data.elapsed);
                const formattedRemaining = formatDuration(remainingSeconds);
                document.getElementById('media-remaining').innerText = 'Remaining time : ' + formattedRemaining;

                document.getElementById('progress').style.width = progress(data.elapsed, data.media.duration);
            }
        })
        .catch(error => console.error('Unable to sync with dashboard:', error));
}

function updatePlaylistState() {
    fetch('/dashboard/running')
    .then(response => response.json())
    .then(data => {
        const container = document.getElementById('current-queue');
        
        if (data && data.program) {
            container.innerHTML = '';
            
            data.program.forEach((item) => {
                const itemDiv = document.createElement('div');
                
                const isPlaying = (item.title === activeMediaTitle);

                if (isPlaying) {
                    itemDiv.className = 'p-2.5 rounded-xl bg-green-800/40 border border-green-800/50 hover:border-slate-700 cursor-pointer animate-pulse';
                } else {
                    itemDiv.className = 'p-2.5 rounded-xl bg-slate-800/40 border border-slate-800/50 hover:border-slate-700 cursor-pointer';
                }
                
                const formattedDuration = formatDuration(item.duration);
                itemDiv.innerHTML = `
                    <p class="text-slate-300 font-medium">${item.title}</p>
                    <span class="text-[10px] text-slate-500">${formattedDuration} • Ready</span>
                `;
                
                container.appendChild(itemDiv);
            });
        }
    })
    .catch(error => console.error('Error :', error));
}

updatePlaylistState();

setInterval(updatePlaylistState, 6000);
setInterval(updateDashboardState, 1000);