/**
 * GPS Map Widget — Hecos
 * ──────────────────────────────────────────────────────────
 * Uses Leaflet.js + OpenStreetMap (CartoDB dark tiles).
 * Features:
 *   - Geocodes the user's home from /api/widgets/map/home
 *   - Drops a 🏠 pin on the home position
 *   - Optionally tracks live GPS via navigator.geolocation.watchPosition()
 *   - Graceful degradation: works even if GPS is denied or profile is empty
 * ──────────────────────────────────────────────────────────
 */

const mapWidget = {
    map: null,
    homeMarker: null,
    liveMarker: null,
    watchId: null,
    isInitialized: false,
    liveGpsEnabled: true,   // can be overridden by config
    homeData: null,

    // ──────────────────────────────────────────
    // LIFECYCLE
    // ──────────────────────────────────────────

    init: function () {
        console.log('[MAP] Widget initialization started...');
        this.fetchHomeLocation();
    },

    toggleBody: function () {
        const body = document.getElementById('mw-body');
        if (!body) return;
        const collapsed = body.classList.toggle('collapsed');
        // Leaflet needs a size invalidation when the container becomes visible again
        if (!collapsed && this.map) {
            setTimeout(() => this.map.invalidateSize(), 350);
        }
    },

    // ──────────────────────────────────────────
    // LEAFLET MAP SETUP
    // ──────────────────────────────────────────

    initMap: function (lat, lon) {
        if (this.isInitialized) return;

        // Wait for Leaflet to be ready
        if (typeof L === 'undefined') {
            console.warn('[MAP] Leaflet not yet loaded, retrying in 500ms...');
            setTimeout(() => this.initMap(lat, lon), 500);
            return;
        }

        // Dark tile layer from CartoDB (free, no API key)
        const darkTiles = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
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
            scrollWheelZoom: false    // prevent accidental scroll in sidebar
        });

        // Enable scroll wheel zoom only on explicit mouse-over of the map
        this.map.on('focus', () => this.map.scrollWheelZoom.enable());
        this.map.on('blur',  () => this.map.scrollWheelZoom.disable());

        this.isInitialized = true;
        console.log('[MAP] Leaflet map initialized at', lat, lon);
    },

    // ──────────────────────────────────────────
    // CUSTOM MARKERS (emoji-based, no external assets)
    // ──────────────────────────────────────────

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
    // HOME LOCATION
    // ──────────────────────────────────────────

    fetchHomeLocation: async function () {
        try {
            const res  = await fetch('/api/widgets/map/home');
            const data = await res.json();

            if (data.ok) {
                this.homeData = data;
                this.renderHome(data.lat, data.lon, data.display_name);
            } else {
                this.showError(data.error || 'Posizione home non disponibile');
            }
        } catch (e) {
            this.showError('Errore di connessione al server');
            console.error('[MAP] fetchHomeLocation error:', e);
        }
    },

    renderHome: function (lat, lon, displayName) {
        // Shorten display name for the header label
        const shortName = this._shortenName(displayName);
        const el = document.getElementById('mw-location');
        if (el) el.textContent = shortName;

        // Show coordinates
        const latEl = document.getElementById('mw-lat');
        const lonEl = document.getElementById('mw-lon');
        if (latEl) latEl.textContent = lat.toFixed(5);
        if (lonEl) lonEl.textContent = lon.toFixed(5);

        const coordsRow = document.getElementById('mw-coords-row');
        if (coordsRow) coordsRow.style.display = 'flex';

        // Hide error badge, show home badge
        this._showBadge('home');

        // Hide placeholder
        this._hidePlaceholder();

        // Init map if not yet done
        this.initMap(lat, lon);

        // Drop the home marker
        if (this.homeMarker) {
            this.homeMarker.setLatLng([lat, lon]);
        } else {
            const icon = this._createIcon('🏠', 'mw-marker-home');
            this.homeMarker = L.marker([lat, lon], { icon })
                .addTo(this.map)
                .bindPopup(`<b>🏠 Casa</b><br>${displayName}`, {
                    className: 'mw-popup'
                });
        }

        this.map.setView([lat, lon], 13);

        // Try live GPS if enabled
        if (this.liveGpsEnabled && 'geolocation' in navigator) {
            this.startLiveGPS();
        }
    },

    // ──────────────────────────────────────────
    // LIVE GPS
    // ──────────────────────────────────────────

    startLiveGPS: function () {
        const options = {
            enableHighAccuracy: true,
            maximumAge: 10000,
            timeout: 15000
        };

        this.watchId = navigator.geolocation.watchPosition(
            (pos) => this.onGPSSuccess(pos),
            (err) => this.onGPSError(err),
            options
        );
        console.log('[MAP] Live GPS watch started, watchId:', this.watchId);
    },

    stopLiveGPS: function () {
        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
            console.log('[MAP] Live GPS watch stopped.');
        }
    },

    onGPSSuccess: function (pos) {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const acc = Math.round(pos.coords.accuracy);

        console.log(`[MAP] Live GPS: lat=${lat}, lon=${lon}, accuracy=${acc}m`);

        // Show live badge
        const liveEl = document.getElementById('mw-badge-live');
        if (liveEl) liveEl.style.display = 'inline-flex';

        // Update GPS note
        const noteEl = document.getElementById('mw-gps-note');
        const noteTxtEl = document.getElementById('mw-gps-note-text');
        if (noteEl && noteTxtEl) {
            noteTxtEl.textContent = `GPS live attivo — precisione ±${acc}m`;
            noteEl.style.display = 'flex';
        }

        // Update or create live marker
        if (this.liveMarker) {
            this.liveMarker.setLatLng([lat, lon]);
            this.liveMarker.getPopup().setContent(
                `<b>📍 Sei qui</b><br>Precisione: ±${acc}m`
            );
        } else {
            if (!this.map) return; // map not ready yet
            const icon = this._createIcon('📍', 'mw-marker-live');
            this.liveMarker = L.marker([lat, lon], { icon, zIndexOffset: 1000 })
                .addTo(this.map)
                .bindPopup(`<b>📍 Sei qui</b><br>Precisione: ±${acc}m`, {
                    className: 'mw-popup'
                });

            // Draw an accuracy circle (subtle, half-opacity)
            this._liveCircle = L.circle([lat, lon], {
                radius: acc,
                color: '#22c55e',
                fillColor: '#22c55e',
                fillOpacity: 0.06,
                weight: 1,
                opacity: 0.4
            }).addTo(this.map);
        }

        // Update accuracy circle position
        if (this._liveCircle) {
            this._liveCircle.setLatLng([lat, lon]);
            this._liveCircle.setRadius(acc);
        }
    },

    onGPSError: function (err) {
        const msgs = {
            1: 'Accesso GPS negato dal browser.',
            2: 'Posizione GPS non disponibile.',
            3: 'Timeout richiesta GPS.'
        };
        const msg = msgs[err.code] || 'Errore GPS sconosciuto.';
        console.warn('[MAP] GPS error:', msg, err);

        // Just hide the live badge silently — home marker still works
        const liveEl = document.getElementById('mw-badge-live');
        if (liveEl) liveEl.style.display = 'none';

        const noteEl = document.getElementById('mw-gps-note');
        if (noteEl) noteEl.style.display = 'none';
    },

    // ──────────────────────────────────────────
    // ERROR DISPLAY
    // ──────────────────────────────────────────

    showError: function (msg) {
        const errBadge  = document.getElementById('mw-badge-error');
        const errText   = document.getElementById('mw-error-text');
        const homeBadge = document.getElementById('mw-badge-home');
        const locEl     = document.getElementById('mw-location');

        if (errBadge)  errBadge.style.display = 'inline-flex';
        if (errText)   errText.textContent = msg;
        if (homeBadge) homeBadge.style.display = 'none';
        if (locEl)     locEl.textContent = 'N/D';

        // Replace placeholder with error message
        const placeholder = document.getElementById('mw-map-placeholder');
        if (placeholder) {
            placeholder.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="color:#ef4444; font-size:22px;"></i>
                <span style="font-size:10px; text-align:center; padding:0 10px; color:var(--muted);">${msg}</span>
                <span style="font-size:9px; color:var(--muted); opacity:0.7;">Configura città/indirizzo nel profilo utente</span>
            `;
        }
        console.warn('[MAP] showError:', msg);
    },

    // ──────────────────────────────────────────
    // HELPERS
    // ──────────────────────────────────────────

    _showBadge: function (which) {
        const badges = { home: 'mw-badge-home', live: 'mw-badge-live', error: 'mw-badge-error' };
        Object.entries(badges).forEach(([key, id]) => {
            const el = document.getElementById(id);
            if (el) el.style.display = (key === which) ? 'inline-flex' : (key === 'live' ? 'none' : 'none');
        });
        // Always keep home visible when there's no error
        if (which !== 'error') {
            const homeEl = document.getElementById('mw-badge-home');
            if (homeEl) homeEl.style.display = 'inline-flex';
        }
    },

    _hidePlaceholder: function () {
        const ph = document.getElementById('mw-map-placeholder');
        if (ph) ph.classList.add('hidden');
        // Force Leaflet to resize after placeholder hides
        setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 100);
    },

    _shortenName: function (name) {
        if (!name) return '';
        // Take the first 2 comma-separated parts (e.g. city, country)
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
