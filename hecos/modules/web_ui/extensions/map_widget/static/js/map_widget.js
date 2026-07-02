/**
 * Simple Maps Widget — Hecos
 * ──────────────────────────────────────────────────────────
 * Uses Leaflet.js + OpenStreetMap (CartoDB dark tiles).
 * Features:
 *   - Selectable location source (Profile, GPS, IP Network)
 *   - Graceful degradation
 * ──────────────────────────────────────────────────────────
 */

const mapWidget = {
    map: null,
    homeMarker: null,
    isInitialized: false,

    // ──────────────────────────────────────────
    // LIFECYCLE
    // ──────────────────────────────────────────

    init: function () {
        console.log('[MAP] Widget initialization started...');
        const savedSource = localStorage.getItem('hecos_map_source') || 'profile';
        const selectEl = document.getElementById('mw-source-selector');
        if (selectEl) selectEl.value = savedSource;
        this.loadSource(savedSource);
    },

    toggleBody: function () {
        const body = document.getElementById('mw-body');
        if (!body) return;
        const collapsed = body.classList.toggle('collapsed');
        if (!collapsed && this.map) {
            setTimeout(() => this.map.invalidateSize(), 350);
        }
    },

    changeSource: function(source) {
        localStorage.setItem('hecos_map_source', source);
        this.loadSource(source);
    },

    loadSource: function(source) {
        // Toggle manual input visibility
        const manualContainer = document.getElementById('mw-manual-input-container');
        if (manualContainer) {
            manualContainer.style.display = (source === 'manual') ? 'flex' : 'none';
        }

        // If manual, and input is empty, wait for user
        if (source === 'manual') {
            const input = document.getElementById('mw-manual-address');
            const savedManual = localStorage.getItem('hecos_map_manual_address');
            if (savedManual && input) input.value = savedManual;
            
            if (input && input.value.trim().length > 0) {
                this.fetchManualLocation();
            } else {
                const placeholder = document.getElementById('mw-map-placeholder');
                if (placeholder) {
                    placeholder.innerHTML = `<i class="fas fa-keyboard"></i><span>Enter address above...</span>`;
                    placeholder.classList.remove('hidden');
                }
                this._showBadge(null);
            }
            return;
        }

        // Reset UI to loading state
        const placeholder = document.getElementById('mw-map-placeholder');
        if (placeholder) {
            placeholder.innerHTML = `<i class="fas fa-spinner fa-spin"></i><span>Loading map...</span>`;
            placeholder.classList.remove('hidden');
        }
        this._showBadge(null);

        // Hide coords row temporarily
        const coordsRow = document.getElementById('mw-coords-row');
        if (coordsRow) coordsRow.style.display = 'none';

        if (source === 'profile') {
            this.fetchHomeLocation();
        } else if (source === 'gps') {
            this.startSingleGPS();
        } else if (source === 'ip') {
            this.fetchIPLocation();
        }
    },

    // ──────────────────────────────────────────
    // LEAFLET MAP SETUP
    // ──────────────────────────────────────────

    initMap: function (lat, lon) {
        if (this.isInitialized) return;

        if (typeof L === 'undefined') {
            console.warn('[MAP] Leaflet not yet loaded, retrying in 500ms...');
            setTimeout(() => this.initMap(lat, lon), 500);
            return;
        }

        const darkTiles = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                subdomains: 'abcd',
                maxZoom: 19
            }
        );

        this.map = L.map('mw-map', {
            center: [lat, lon],
            zoom: 13,
            zoomControl: true,
            attributionControl: true,
            layers: [darkTiles],
            scrollWheelZoom: false
        });

        this.map.on('focus', () => this.map.scrollWheelZoom.enable());
        this.map.on('blur',  () => this.map.scrollWheelZoom.disable());

        // Handle container resize (e.g. user stretches the widget vertically)
        if ('ResizeObserver' in window) {
            const ro = new ResizeObserver(() => {
                if (this.map) this.map.invalidateSize();
            });
            const container = document.getElementById('mw-map-container');
            if (container) ro.observe(container);
        }

        this.isInitialized = true;
    },

    _createIcon: function (emoji, cssClass) {
        return L.divIcon({
            className: cssClass,
            html: `<span style="line-height:32px; font-size:18px;">${emoji}</span>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        });
    },

    // ──────────────────────────────────────────
    // DATA FETCHERS
    // ──────────────────────────────────────────

    fetchHomeLocation: async function () {
        try {
            const res  = await fetch('/api/widgets/map/home');
            const data = await res.json();

            if (data.ok) {
                this.renderHome(data.lat, data.lon, data.display_name, 'profile');
            } else {
                this.showError(data.error || 'Home position unavailable. Check Address and City.');
            }
        } catch (e) {
            this.showError('Connection error to backend server.');
        }
    },

    fetchIPLocation: async function() {
        try {
            const res = await fetch('https://ipapi.co/json/');
            const data = await res.json();
            if (data && data.latitude && data.longitude) {
                this.renderHome(data.latitude, data.longitude, `${data.city || 'Unknown'}, ${data.region || ''} (IP)`, 'ip');
            } else {
                this.showError('Unable to get IP location (rate limit?).');
            }
        } catch(e) {
            this.showError('IP API connection error.');
        }
    },

    fetchManualLocation: async function() {
        const input = document.getElementById('mw-manual-address');
        if (!input) return;
        const query = input.value.trim();
        if (!query) return;

        localStorage.setItem('hecos_map_manual_address', query);

        const placeholder = document.getElementById('mw-map-placeholder');
        if (placeholder) {
            placeholder.innerHTML = `<i class="fas fa-spinner fa-spin"></i><span>Loading map...</span>`;
            placeholder.classList.remove('hidden');
        }
        this._showBadge(null);

        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`);
            const data = await res.json();
            if (data && data.length > 0) {
                const item = data[0];
                this.renderHome(parseFloat(item.lat), parseFloat(item.lon), item.display_name, 'manual');
            } else {
                this.showError('Address not found on OpenStreetMap.');
            }
        } catch (e) {
            this.showError('Geocoding API connection error.');
        }
    },

    startSingleGPS: function() {
        if (!('geolocation' in navigator)) {
            this.showError('Geolocation not supported by the browser.');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const acc = Math.round(pos.coords.accuracy);
                this.renderHome(lat, lon, `Sensor Detection (Accuracy: ±${acc}m)`, 'gps');
            },
            (err) => {
                const msgs = {
                    1: 'GPS access denied by browser.',
                    2: 'GPS position unavailable.',
                    3: 'GPS request timeout.'
                };
                this.showError(msgs[err.code] || 'Unknown GPS error.');
            },
            { enableHighAccuracy: true, timeout: 15000 }
        );
    },

    // ──────────────────────────────────────────
    // RENDER
    // ──────────────────────────────────────────

    renderHome: function (lat, lon, displayName, sourceType) {
        if (typeof L === 'undefined') {
            setTimeout(() => this.renderHome(lat, lon, displayName, sourceType), 500);
            return;
        }

        const shortName = this._shortenName(displayName);
        const locEl = document.getElementById('mw-location');
        if (locEl) locEl.textContent = shortName;

        const latEl = document.getElementById('mw-lat');
        const lonEl = document.getElementById('mw-lon');
        if (latEl) latEl.textContent = lat.toFixed(5);
        if (lonEl) lonEl.textContent = lon.toFixed(5);

        const coordsRow = document.getElementById('mw-coords-row');
        if (coordsRow) coordsRow.style.display = 'flex';

        this._showBadge(sourceType === 'profile' ? 'home' : 'live');
        this._hidePlaceholder();
        this.initMap(lat, lon);

        let emoji = '📍';
        if (sourceType === 'profile') emoji = '🏠';
        if (sourceType === 'ip') emoji = '🌐';
        if (sourceType === 'manual') emoji = '🔍';
        
        const icon = this._createIcon(emoji, 'mw-marker-home');

        if (this.homeMarker) {
            this.homeMarker.setIcon(icon);
            this.homeMarker.setLatLng([lat, lon]);
            this.homeMarker.getPopup().setContent(`<b>${emoji} Position</b><br>${displayName}`);
        } else {
            this.homeMarker = L.marker([lat, lon], { icon })
                .addTo(this.map)
                .bindPopup(`<b>${emoji} Position</b><br>${displayName}`, {
                    className: 'mw-popup'
                });
        }

        this.map.setView([lat, lon], 13);
    },

    showError: function (msg) {
        const errBadge  = document.getElementById('mw-badge-error');
        const errText   = document.getElementById('mw-error-text');
        
        if (errBadge)  errBadge.style.display = 'inline-flex';
        if (errText)   errText.textContent = 'Location Error';
        this._showBadge('error');

        const placeholder = document.getElementById('mw-map-placeholder');
        if (placeholder) {
            placeholder.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="color:#ef4444; font-size:22px;"></i>
                <span style="font-size:10px; text-align:center; padding:0 10px; color:var(--muted);">${msg}</span>
            `;
            placeholder.classList.remove('hidden');
        }
    },

    // ──────────────────────────────────────────
    // HELPERS
    // ──────────────────────────────────────────

    _showBadge: function (which) {
        const badges = { home: 'mw-badge-home', live: 'mw-badge-live', error: 'mw-badge-error' };
        Object.entries(badges).forEach(([key, id]) => {
            const el = document.getElementById(id);
            if (el) el.style.display = (key === which) ? 'inline-flex' : 'none';
        });
    },

    _hidePlaceholder: function () {
        const ph = document.getElementById('mw-map-placeholder');
        if (ph) ph.classList.add('hidden');
        setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 100);
    },

    _shortenName: function (name) {
        if (!name) return '';
        const parts = name.split(',');
        if (parts.length >= 2) {
            return `${parts[0].trim()}, ${parts[1].trim()}`;
        }
        return name.length > 30 ? name.substring(0, 28) + '…' : name;
    }
};

// ── Bootstrap ──
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => mapWidget.init());
} else {
    mapWidget.init();
}
