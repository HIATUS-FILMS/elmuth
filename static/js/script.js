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