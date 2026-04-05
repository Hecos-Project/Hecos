/**
 * mobile_logic.js
 * Controls dynamic behavior for mobile screens (Hamburger menu, touch gestures, etc)
 */

document.addEventListener('DOMContentLoaded', () => {
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobile-overlay');

    if (mobileBtn && sidebar && overlay) {
        // Toggle Sidebar on Hamburger click
        mobileBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });

        // Close Sidebar on Overlay click
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });

        // Optional: Close Sidebar if a nav link is clicked inside it
        const sidebarLinks = sidebar.querySelectorAll('.sidebar-btn, .sidebar-bottom a');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                    overlay.classList.remove('active');
                }
            });
        });
        
        // Touch swipe to close (basic implementation)
        let touchstartX = 0;
        let touchendX = 0;
        
        sidebar.addEventListener('touchstart', e => {
            touchstartX = e.changedTouches[0].screenX;
        });
        
        sidebar.addEventListener('touchend', e => {
            touchendX = e.changedTouches[0].screenX;
            if (touchstartX - touchendX > 50) {
                // Swiped Left
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        });
    }
});
