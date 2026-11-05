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

let remainingTimeMs = 0;
let lastSyncTime = Date.now();

setInterval(() => {
    fetch('/dashboard/status/playlist_remaining')
        .then(response => response.json())
        .then(data => {
            const parts = data.remaining.split(':');
            if (parts.length === 4) {
                const h = parseInt(parts[0], 10);
                const m = parseInt(parts[1], 10);
                const s = parseInt(parts[2], 10);
                const ms = parseInt(parts[3], 10);
                remainingTimeMs = ((h * 3600 + m * 60 + s) * 1000) + ms;
                lastSyncTime = Date.now();
            }
        });
}, 1000);

function updateRemainingClock() {
    if (remainingTimeMs > 0) {
        const elapsed = Date.now() - lastSyncTime;
        let currentMs = Math.max(0, remainingTimeMs - elapsed);

        const hours = Math.floor(currentMs / 3600000);
        const minutes = Math.floor((currentMs % 3600000) / 60000);
        const seconds = Math.floor((currentMs % 60000) / 1000);
        const milliseconds = currentMs % 1000;

        const formatted = 
            String(hours).padStart(2, '0') + ':' +
            String(minutes).padStart(2, '0') + ':' +
            String(seconds).padStart(2, '0') + ':' +
            String(milliseconds).padStart(3, '0');

        document.getElementById('playlist-remaining').textContent = formatted;
    }
    requestAnimationFrame(updateRemainingClock);
}

requestAnimationFrame(updateRemainingClock);