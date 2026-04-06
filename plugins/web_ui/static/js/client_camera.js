/**
 * MODULE: client_camera.js
 * PURPOSE: Shows a visible tap-to-capture button when the AI requests a client camera snapshot.
 *          The button is injected into the .msg container (parent of the AI bubble) so it
 *          survives innerHTML re-renders. The button click IS a valid user gesture, enabling
 *          the browser to open the native device camera.
 */

window.ClientCameraManager = {

    /**
     * Injects a visible camera capture button into the parent of the given AI bubble.
     * Called directly by chat_logic.js when it receives a dedicated 'camera_request' SSE event.
     * @param {HTMLElement} bubble - The AI chat bubble element
     */
    showCameraButton: function(bubble) {
        // Avoid duplicating the button
        if (document.getElementById('client-camera-btn')) return;

        // Create the hidden file input
        let camInput = document.getElementById('client-camera-capture-field');
        if (!camInput) {
            camInput = document.createElement('input');
            camInput.type = 'file';
            camInput.accept = 'image/*';
            camInput.capture = 'environment'; // 'environment' = rear camera on mobile
            camInput.id = 'client-camera-capture-field';
            camInput.style.display = 'none';

            camInput.onchange = (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    if (typeof window.handleFiles === 'function') {
                        window.handleFiles(e.target.files, 'img');
                        // Give the upload chip a moment to register, then auto-send
                        setTimeout(() => {
                            if (typeof window.sendMessage === 'function') {
                                window.sendMessage();
                            }
                        }, 150);
                    }
                }
                // Remove the button after use to keep chat clean
                const btn = document.getElementById('client-camera-btn');
                if (btn) btn.remove();
            };
            document.body.appendChild(camInput);
        }
        camInput.value = ''; // Reset so re-use works

        // Create the visible button
        const btn = document.createElement('button');
        btn.id = 'client-camera-btn';
        btn.innerHTML = '📷 Tap here to take a photo';
        btn.style.cssText = `
            display: inline-block;
            margin-top: 12px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6e40c9, #9f5fee);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            letter-spacing: 0.3px;
            box-shadow: 0 2px 12px rgba(110,64,201,0.4);
            transition: opacity 0.2s;
        `;
        btn.addEventListener('mouseenter', () => btn.style.opacity = '0.85');
        btn.addEventListener('mouseleave', () => btn.style.opacity = '1');

        // A button click event IS a valid user gesture — browser will grant camera access
        btn.addEventListener('click', () => camInput.click());

        // Inject into the .msg PARENT, not inside the bubble itself.
        // The bubble innerHTML is rewritten on every token event; the parent is stable.
        const container = bubble ? (bubble.parentElement || bubble) : document.getElementById('chat-area');
        if (container) container.appendChild(btn);
    }
};
