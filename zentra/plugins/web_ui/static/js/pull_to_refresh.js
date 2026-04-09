/**
 * pull_to_refresh.js
 * Implements a custom pull-to-refresh gesture for the Chat UI.
 */

(function() {
    let touchStartY = 0;
    let touchMoveY = 0;
    let isPulling = false;
    const threshold = 70; // px to trigger refresh
    const maxPull = 100;   // max visual pull distance

    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return;

    // Create indicator element
    const indicator = document.createElement('div');
    indicator.id = 'pull-to-refresh-indicator';
    indicator.innerHTML = '<span class="ptr-icon">▼</span>';
    chatArea.prepend(indicator);

    const icon = indicator.querySelector('.ptr-icon');

    chatArea.addEventListener('touchstart', (e) => {
        if (chatArea.scrollTop <= 0) {
            touchStartY = e.touches[0].screenY;
        } else {
            touchStartY = 0;
        }
    }, { passive: true });

    chatArea.addEventListener('touchmove', (e) => {
        const touchY = e.touches[0].screenY;
        
        if (touchStartY > 0 && chatArea.scrollTop <= 0 && touchY > touchStartY) {
            isPulling = true;
            touchMoveY = touchY - touchStartY;
            
            // Apply resistance
            const pullDistance = Math.min(touchMoveY * 0.4, maxPull);
            
            indicator.style.transform = `translateY(${pullDistance}px)`;
            indicator.style.opacity = Math.min(pullDistance / threshold, 1);
            
            // Rotate icon or change color
            if (pullDistance >= 60) {
                icon.style.transform = 'rotate(180deg)';
                icon.style.color = 'var(--accent2)';
            } else {
                icon.style.transform = 'rotate(0deg)';
                icon.style.color = 'var(--accent)';
            }
        } else {
            isPulling = false;
        }
    }, { passive: true });

    chatArea.addEventListener('touchend', () => {
        if (isPulling) {
            const pullDistance = Math.min(touchMoveY * 0.4, maxPull);
            
            if (pullDistance >= 60) {
                // Trigger refresh
                icon.innerHTML = '↻';
                icon.classList.add('ptr-spinning');
                indicator.style.transform = `translateY(40px)`;
                
                setTimeout(() => {
                    window.location.reload();
                }, 400);
            } else {
                // Reset
                indicator.style.transform = 'translateY(0)';
                indicator.style.opacity = '0';
            }
        }
        touchStartY = 0;
        touchMoveY = 0;
        isPulling = false;
    });
})();
