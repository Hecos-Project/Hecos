/**
 * ws_avatar.js — Welcome Avatar 3D Card
 * Part of: welcome_screen/ module
 *
 * Renders the 3D flipping card showing the active soul/persona avatar.
 * Front: Hecos logo. Back: active persona avatar (image or video).
 */
(function() {
    'use strict';

    // Inject CSS for the 3D flip animation
    const style = document.createElement('style');
    style.textContent = `
        .hecos-welcome-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            min-height: 400px;
            color: var(--text);
            font-family: inherit;
            animation: wsAvatarFadeIn 0.5s ease-out;
            pointer-events: none;
        }
        @keyframes wsAvatarFadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hecos-welcome-card-scene {
            width: 120px; height: 120px;
            perspective: 600px; margin-bottom: 24px;
        }
        .hecos-welcome-card {
            width: 100%; height: 100%;
            position: relative;
            transition: transform 0.8s cubic-bezier(0.4, 0.0, 0.2, 1);
            transform-style: preserve-3d;
        }
        .hecos-welcome-card.is-flipped { transform: rotateY(180deg); }
        .hecos-welcome-card-face {
            position: absolute; width: 100%; height: 100%;
            backface-visibility: hidden; border-radius: 50%;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: flex; align-items: center; justify-content: center;
            overflow: hidden; background: #1e1e1e;
        }
        .hecos-welcome-card-front {
            transform: rotateY(0deg);
            border: 2px solid rgba(108, 140, 255, 0.3);
        }
        .hecos-welcome-card-front img {
            width: 70%; height: 70%; object-fit: contain;
            filter: drop-shadow(0 0 10px rgba(108,140,255,0.4));
        }
        .hecos-welcome-card-back {
            transform: rotateY(180deg);
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        .hecos-welcome-card-back img,
        .hecos-welcome-card-back video {
            width: 100%; height: 100%; object-fit: cover;
        }
        .hecos-welcome-text {
            text-align: center; opacity: 0;
            transform: translateY(10px);
            transition: all 0.5s ease-out 0.4s;
        }
        .hecos-welcome-text.show { opacity: 1; transform: translateY(0); }
        .hecos-welcome-text .hecos-welcome-title {
            font-size: 14px; font-weight: 500;
            color: var(--muted); margin-bottom: 4px; letter-spacing: 0.5px;
        }
        .hecos-welcome-name {
            font-size: 24px; font-weight: 700;
            background: var(--accent-g);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }
        .hecos-welcome-preset {
            font-size: 0.85rem; color: var(--accent, #6c8cff);
            background: rgba(108, 140, 255, 0.1);
            padding: 4px 12px; border-radius: 12px;
            display: inline-block; border: 1px solid rgba(108, 140, 255, 0.2);
            pointer-events: auto;
        }
    `;
    document.head.appendChild(style);

    /**
     * Get current soul info from global state.
     */
    function getSoulInfo() {
        const personaName = window.HecosPersonaName || 'Hecos System Soul';
        const avatarSrc = window.HecosAvatar || '/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';
        const isVideo = window.HecosAvatarType === 'video';

        let activePreset = null;
        if (window.soState && window.soState.activeSoulId) {
            activePreset = window.soState.activeSoulId;
        } else if (window.sfState && window.sfState.activeSoulId) {
            activePreset = window.sfState.activeSoulId;
        }

        const isDefaultHecos = personaName.toLowerCase().includes('hecos') && !activePreset;

        return { personaName, avatarSrc, isVideo, activePreset, isDefaultHecos };
    }

    /**
     * Render the Avatar 3D card into the chat area.
     * @param {HTMLElement} chatArea
     * @param {object} [opts] - { hidden: bool } if true, container starts hidden (for hybrid)
     * @returns {HTMLElement} The container element
     */
    function render(chatArea, opts) {
        const old = document.getElementById('hecos-welcome-screen');
        if (old) old.remove();

        const soul = getSoulInfo();
        const container = document.createElement('div');
        container.id = 'hecos-welcome-screen';
        container.className = 'hecos-welcome-container';

        if (opts && opts.hidden) {
            container.style.display = 'none';
        }

        const backMediaHtml = soul.isVideo
            ? `<video src="${soul.avatarSrc}" autoplay loop muted playsinline></video>`
            : `<img src="${soul.avatarSrc}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png'">`;

        const cleanName = soul.personaName.replace(/_/g, ' ').replace(/\.yaml$/i, '');

        const isFlippedClass = (opts && opts.flipped && !soul.isDefaultHecos) ? ' is-flipped' : '';
        const isShowClass = (opts && opts.flipped) ? ' show' : '';

        container.innerHTML = `
            <div class="hecos-welcome-card-scene">
                <div class="hecos-welcome-card${isFlippedClass}" id="hecos-welcome-card">
                    <div class="hecos-welcome-card-face hecos-welcome-card-front">
                        <img src="/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" alt="Hecos">
                    </div>
                    <div class="hecos-welcome-card-face hecos-welcome-card-back">
                        ${backMediaHtml}
                    </div>
                </div>
            </div>
            <div class="hecos-welcome-text${isShowClass}" id="hecos-welcome-text">
                <div class="hecos-welcome-title">Now you are talking to</div>
                <div class="hecos-welcome-name">${cleanName}</div>
                ${soul.activePreset ? `<div class="hecos-welcome-preset" title="Global Preset"><i class="fas fa-bolt"></i> ${soul.activePreset}</div>` : ''}
            </div>
        `;

        chatArea.appendChild(container);
        return container;
    }

    /**
     * Trigger the flip + text reveal animation.
     */
    function animate() {
        const soul = getSoulInfo();
        const card = document.getElementById('hecos-welcome-card');
        const text = document.getElementById('hecos-welcome-text');
        if (text) text.classList.add('show');
        if (card && !soul.isDefaultHecos) card.classList.add('is-flipped');
    }

    /**
     * Remove the avatar welcome element.
     */
    function remove() {
        const el = document.getElementById('hecos-welcome-screen');
        if (el) el.remove();
    }

    window.WelcomeAvatar = { render, animate, remove, getSoulInfo };
})();
