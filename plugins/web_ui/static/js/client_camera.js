/**
 * MODULE: client_camera.js
 * PURPOSE: Extends the WebUI with the ability to trigger the native device camera 
 *          when requested by the AI. Intercepts the streaming response and shows
 *          a tap-to-capture button (required due to browser security: programmatic
 *          file input clicks are blocked unless initiated by a real user gesture).
 */

window.ClientCameraManager = {
    triggerToken: "[CAMERA_SNAPSHOT_REQUEST]",

    /**
     * Inspects the incoming AI text stream. If the trigger token is detected,
     * strips it from the output and injects a camera capture button into the bubble.
     * @param {string} currentText - Current accumulated AI response text
     * @param {string} sessionId   - Session ID to prevent multiple triggers
     * @param {HTMLElement} bubble - The AI chat bubble DOM element to inject the button into
     */
    interceptStream: function(currentText, sessionId, bubble) {
        if (currentText.includes(this.triggerToken)) {
            currentText = currentText.replace(this.triggerToken, "").trim();

            // Prevent multiple triggers for the same AI stream session
            if (window._clientCameraTriggeredSession !== sessionId) {
                window._clientCameraTriggeredSession = sessionId;
                this._injectCaptureButton(bubble);
            }
        }
        return currentText;
    },

    _injectCaptureButton: function(bubble) {
        // Avoid duplicating the button
        if (document.getElementById('client-camera-btn')) return;

        // Create the hidden file input
        let camInput = document.getElementById('client-camera-capture-field');
        if (!camInput) {
            camInput = document.createElement('input');
            camInput.type = 'file';
            camInput.accept = 'image/*';
            camInput.capture = 'environment';
            camInput.id = 'client-camera-capture-field';
            camInput.style.display = 'none';

            camInput.onchange = (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    if (typeof window.handleFiles === 'function') {
                        window.handleFiles(e.target.files, 'img');
                        // Give the upload chip a moment to register before sending
                        setTimeout(() => {
                            if (typeof window.sendMessage === 'function') {
                                window.sendMessage();
                            }
                        }, 150);
                    }
                }
                // Remove button after use
                const btn = document.getElementById('client-camera-btn');
                if (btn) btn.remove();
            };
            document.body.appendChild(camInput);
        }
        camInput.value = '';

        // Create a visible, tappable button and inject it directly into the AI bubble
        const btn = document.createElement('button');
        btn.id = 'client-camera-btn';
        btn.innerHTML = '📷 Tap here to open camera';
        btn.style.cssText = `
            display: block;
            margin-top: 12px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6e40c9, #9f5fee);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            letter-spacing: 0.3px;
            box-shadow: 0 2px 12px rgba(110, 64, 201, 0.4);
            transition: opacity 0.2s;
        `;
        btn.addEventListener('mouseenter', () => btn.style.opacity = '0.85');
        btn.addEventListener('mouseleave', () => btn.style.opacity = '1');

        // This click listener IS a valid user gesture — camera access will be granted
        btn.addEventListener('click', () => {
            camInput.click();
        });

        if (bubble) {
            bubble.appendChild(btn);
        } else {
            // Fallback: append to chat area
            const chatArea = document.getElementById('chat-area');
            if (chatArea) chatArea.appendChild(btn);
        }
    }
};
