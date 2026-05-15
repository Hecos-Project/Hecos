/**
 * Hecos WebUI - Mapper Logic for Plugins
 * Handles Drive, Browser, and Remote Triggers.
 */

function populateDriveUI() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.DRIVE) return;
    const d = c.plugins.DRIVE;
    setVal('drive-root-dir', d.root_dir || '');
    setVal('drive-max-upload-mb', d.max_upload_mb ?? 100);
    setVal('drive-allowed-ext', d.allowed_extensions || '');

    const exts = d.extensions || {};
    
    // Editor
    const ed = exts.editor || {};
    setCheck('drive-editor-autosave', ed.autosave ?? false);
    setVal('drive-editor-autosave-interval', ed.autosave_interval ?? 30);
    setCheck('drive-editor-confirm-close', ed.confirm_close ?? true);
    setCheck('drive-editor-backup', ed.backup_on_save ?? false);
    setVal('drive-editor-theme', ed.theme || 'vs-dark');
    setVal('drive-editor-tab-size', ed.tab_size ?? 4);
    setCheck('drive-editor-line-numbers', ed.line_numbers ?? true);
    setCheck('drive-editor-word-wrap', ed.word_wrap ?? false);
    setCheck('drive-editor-minimap', ed.minimap ?? true);
    setVal('drive-editor-max-file-mb', ed.max_file_mb ?? 10);
    setVal('drive-editor-readonly-ext', ed.readonly_ext || '');

    // Media Viewer
    const mv = exts.media_viewer || {};
    setVal('drive-viewer-default-zoom', mv.default_zoom || 'fit');
    setCheck('drive-viewer-show-exif', mv.show_exif ?? false);
    setCheck('drive-viewer-slideshow', mv.slideshow ?? false);
    setVal('drive-viewer-slideshow-interval', mv.slideshow_interval ?? 5);
    setCheck('drive-viewer-video-autoplay', mv.video_autoplay ?? false);
    setCheck('drive-viewer-video-loop', mv.video_loop ?? false);
    setCheck('drive-viewer-video-controls', mv.video_controls ?? true);
    setCheck('drive-viewer-audio-autoplay', mv.audio_autoplay ?? false);
    setCheck('drive-viewer-audio-waveform', mv.audio_waveform ?? true);
    setVal('drive-viewer-image-ext', mv.image_ext || 'jpg,jpeg,png,gif,webp,svg,bmp,ico');
    setVal('drive-viewer-video-ext', mv.video_ext || 'mp4,webm,mkv,avi,mov');
    setVal('drive-viewer-audio-ext', mv.audio_ext || 'mp3,ogg,wav,flac,aac,m4a');
}

function buildDrivePayload() {
    const rootEl = document.getElementById('drive-root-dir');
    if (!rootEl) return {}; // Not in DOM
    const c = window.cfg && window.cfg.plugins && window.cfg.plugins.DRIVE ? window.cfg.plugins.DRIVE : {};
    const exts = c.extensions || {};
    const newExts = JSON.parse(JSON.stringify(exts));

    if (document.getElementById('drive-editor-theme')) {
        newExts.editor = Object.assign({}, newExts.editor, {
            autosave: getC('drive-editor-autosave', exts.editor?.autosave),
            autosave_interval: parseInt(getV('drive-editor-autosave-interval', exts.editor?.autosave_interval)) || 30,
            confirm_close: getC('drive-editor-confirm-close', exts.editor?.confirm_close),
            backup_on_save: getC('drive-editor-backup', exts.editor?.backup_on_save),
            theme: getV('drive-editor-theme', exts.editor?.theme) || 'vs-dark',
            tab_size: parseInt(getV('drive-editor-tab-size', exts.editor?.tab_size)) || 4,
            line_numbers: getC('drive-editor-line-numbers', exts.editor?.line_numbers),
            word_wrap: getC('drive-editor-word-wrap', exts.editor?.word_wrap),
            minimap: getC('drive-editor-minimap', exts.editor?.minimap),
            max_file_mb: parseInt(getV('drive-editor-max-file-mb', exts.editor?.max_file_mb)) || 10,
            readonly_ext: getV('drive-editor-readonly-ext', exts.editor?.readonly_ext)
        });
    }

    if (document.getElementById('drive-viewer-default-zoom')) {
        newExts.media_viewer = Object.assign({}, newExts.media_viewer, {
            default_zoom: getV('drive-viewer-default-zoom', exts.media_viewer?.default_zoom) || 'fit',
            show_exif: getC('drive-viewer-show-exif', exts.media_viewer?.show_exif),
            slideshow: getC('drive-viewer-slideshow', exts.media_viewer?.slideshow),
            slideshow_interval: parseInt(getV('drive-viewer-slideshow-interval', exts.media_viewer?.slideshow_interval)) || 5,
            video_autoplay: getC('drive-viewer-video-autoplay', exts.media_viewer?.video_autoplay),
            video_loop: getC('drive-viewer-video-loop', exts.media_viewer?.video_loop),
            video_controls: getC('drive-viewer-video-controls', exts.media_viewer?.video_controls),
            audio_autoplay: getC('drive-viewer-audio-autoplay', exts.media_viewer?.audio_autoplay),
            audio_waveform: getC('drive-viewer-audio-waveform', exts.media_viewer?.audio_waveform),
            image_ext: getV('drive-viewer-image-ext', exts.media_viewer?.image_ext),
            video_ext: getV('drive-viewer-video-ext', exts.media_viewer?.video_ext),
            audio_ext: getV('drive-viewer-audio-ext', exts.media_viewer?.audio_ext)
        });
    }

    return {
        plugins: {
            DRIVE: {
                root_dir: getV('drive-root-dir', c.root_dir || '').trim(),
                max_upload_mb: parseInt(getV('drive-max-upload-mb', c.max_upload_mb)) || 100,
                allowed_extensions: getV('drive-allowed-ext', c.allowed_extensions || '').trim(),
                extensions: newExts
            }
        }
    };
}

function populateRemoteTriggersUI() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.REMOTE_TRIGGERS) return;
    const settings = c.plugins.REMOTE_TRIGGERS.settings || {};
    setCheck('rt-enable-mediasession', settings.enable_mediasession ?? true);
    setCheck('rt-enable-volume-keys', settings.enable_volume_keys ?? true);
    setCheck('rt-enable-volume-loop', settings.enable_volume_loop ?? false);
    setCheck('rt-feedback-sounds', settings.feedback_sounds ?? true);
    setCheck('rt-visual-indicator', settings.visual_indicator ?? true);
}

function buildRemoteTriggersPayload() {
    const c = window.cfg;
    const settings = (c.plugins && c.plugins.REMOTE_TRIGGERS) ? (c.plugins.REMOTE_TRIGGERS.settings || {}) : {};
    return {
        plugins: {
            REMOTE_TRIGGERS: {
                settings: {
                    enable_mediasession: getC('rt-enable-mediasession', settings.enable_mediasession),
                    enable_volume_keys: getC('rt-enable-volume-keys', settings.enable_volume_keys),
                    enable_volume_loop: getC('rt-enable-volume-loop', settings.enable_volume_loop),
                    feedback_sounds: getC('rt-feedback-sounds', settings.feedback_sounds),
                    visual_indicator: getC('rt-visual-indicator', settings.visual_indicator)
                }
            }
        }
    };
}

function populateBrowserUI() {
    const c = window.cfg;
    if (!c) return;
    const browserConfig = (c.plugins && c.plugins['BROWSER']) ? c.plugins['BROWSER'] : {};
    setCheck('browser-enabled', browserConfig.enabled !== false);
    setCheck('browser-headless', browserConfig.headless ?? false);
    setCheck('browser-block-ads', browserConfig.block_ads ?? true);
    setVal('browser-startup-url', browserConfig.startup_url || 'http://localhost:7070');
    setVal('browser-timeout', browserConfig.default_timeout || 10000);
    setVal('browser-engine', browserConfig.browser_type || 'chromium');
}

// Bridges for global scope
window.populateDriveUI = populateDriveUI;
window.buildDrivePayload = buildDrivePayload;
window.populateRemoteTriggersUI = populateRemoteTriggersUI;
window.buildRemoteTriggersPayload = buildRemoteTriggersPayload;
window.populateBrowserUI = populateBrowserUI;
