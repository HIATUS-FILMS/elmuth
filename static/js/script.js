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