/**
 * HBS Utility Scripts
 */

const HBSUtils = {
    showToast: function(message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'hbs-toast';
        toast.innerText = message;
        
        document.body.appendChild(toast);
        
        // Trigger reflow to enable transition
        void toast.offsetWidth;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

window.HBSUtils = HBSUtils;
