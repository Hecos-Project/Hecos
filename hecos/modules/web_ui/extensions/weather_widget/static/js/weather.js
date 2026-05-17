const weatherWidget = {
    pollInterval: null,

    init: function() {
        console.log("[WEATHER] Widget initialization started...");
        this.fetchData();
        // Poll every 30 mins
        this.pollInterval = setInterval(() => this.fetchData(), 30 * 60 * 1000);
    },

    toggleBody: function() {
        const body = document.getElementById('ww-body');
        if (body) {
            body.classList.toggle('collapsed');
        }
    },

    getIconClass: function(wmoCode) {
        const codeMap = {
            0: 'fa-sun',
            1: 'fa-sun', 2: 'fa-cloud-sun', 3: 'fa-cloud',
            45: 'fa-smog', 48: 'fa-smog',
            51: 'fa-cloud-rain', 53: 'fa-cloud-rain', 55: 'fa-cloud-showers-heavy',
            56: 'fa-icicles', 57: 'fa-icicles',
            61: 'fa-cloud-rain', 63: 'fa-cloud-rain', 65: 'fa-cloud-showers-heavy',
            66: 'fa-snowflake', 67: 'fa-snowflake',
            71: 'fa-snowflake', 73: 'fa-snowflake', 75: 'fa-snowflake',
            77: 'fa-snowflake',
            80: 'fa-cloud-showers-water', 81: 'fa-cloud-showers-water', 82: 'fa-cloud-showers-heavy',
            85: 'fa-snowflake', 86: 'fa-snowflake',
            95: 'fa-bolt', 96: 'fa-bolt', 99: 'fa-poo-storm'
        };
        return codeMap[wmoCode] || 'fa-cloud';
    },

    getDescription: function(wmoCode) {
        const descMap = {
            0: "Sereno",
            1: "Prevalentemente sereno", 2: "Parzialmente nuvoloso", 3: "Coperto",
            45: "Nebbia", 48: "Nebbia di brina",
            51: "Pioggerellina", 53: "Pioggerellina moderata", 55: "Pioggerellina densa",
            61: "Pioggia leggera", 63: "Pioggia moderata", 65: "Pioggia forte",
            71: "Neve leggera", 73: "Neve moderata", 75: "Neve forte",
            80: "Rovesci leggeri", 81: "Rovesci moderati", 82: "Rovesci violenti",
            95: "Temporale", 96: "Tempesta con grandine", 99: "Tempesta violenta"
        };
        return descMap[wmoCode] || "Sconosciuto";
    },

    getDayName: function(dateStr) {
        const d = new Date(dateStr);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        if (d.toDateString() === today.toDateString()) return "Oggi";
        if (d.toDateString() === tomorrow.toDateString()) return "Domani";
        
        return d.toLocaleDateString('it-IT', { weekday: 'short' }).replace(/^\w/, c => c.toUpperCase());
    },

    render: function(data) {
        if (!data || data.error) {
            document.getElementById('ww-location').textContent = "Errore";
            document.getElementById('ww-desc').textContent = data ? data.error : "Failed to load";
            document.getElementById('ww-icon-main').className = 'fas fa-exclamation-triangle';
            return;
        }

        const current = data.current;
        const daily = data.daily;

        document.getElementById('ww-location').textContent = data.location;
        document.getElementById('ww-temp').textContent = Math.round(current.temperature_2m) + "°";
        document.getElementById('ww-hum').textContent = current.relative_humidity_2m + "%";
        document.getElementById('ww-wind').textContent = current.wind_speed_10m + " km/h";
        
        let desc = this.getDescription(current.weather_code);
        // Additional info for rain or night
        if (!current.is_day && [0,1,2].includes(current.weather_code)) {
             desc = desc.replace("sereno", "sereno (Notte)").replace("Sereno", "Notte stellata");
        }
        document.getElementById('ww-desc').textContent = desc;
        
        // Handle Moon icons for clear night
        let mainIconClass = this.getIconClass(current.weather_code);
        if (!current.is_day) {
            if (current.weather_code === 0 || current.weather_code === 1) mainIconClass = 'fa-moon';
            if (current.weather_code === 2) mainIconClass = 'fa-cloud-moon';
        }
        document.getElementById('ww-icon-main').className = `fas ${mainIconClass}`;
        
        // Render 3-day forecast
        const forecastList = document.getElementById('ww-forecast');
        forecastList.innerHTML = '';
        
        // Show next 3 days
        const maxDays = Math.min(3, daily.time.length);
        for (let i = 0; i < maxDays; i++) {
            const dayName = this.getDayName(daily.time[i]);
            const iconCls = this.getIconClass(daily.weather_code[i]);
            const tMin = Math.round(daily.temperature_2m_min[i]);
            const tMax = Math.round(daily.temperature_2m_max[i]);
            
            forecastList.innerHTML += `
                <div class="ww-forecast-item">
                    <span class="ww-f-day">${dayName}</span>
                    <span class="ww-f-icon"><i class="fas ${iconCls}"></i></span>
                    <span class="ww-f-temp">${tMin} / <span class="max">${tMax}</span></span>
                </div>
            `;
        }
    },

    fetchData: async function() {
        try {
            const res = await fetch('/api/widgets/weather');
            const result = await res.json();
            if (result.ok && result.data) {
                this.render(result.data);
            } else {
                this.render({ error: result.error || "Network error" });
            }
        } catch (e) {
            this.render({ error: "Connection failed" });
        }
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => weatherWidget.init());
} else {
    weatherWidget.init();
}
