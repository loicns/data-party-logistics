/* ================================================================
   DATA PARTY LOGISTICS — Port Operations Intelligence
   Application Logic + Realistic Mock Data
   ================================================================ */

// ---------------------------------------------------------------------------
// PORT DATA (realistic, inspired by Portcast metrics)
// ---------------------------------------------------------------------------

const PORTS = {
    NLRTM: {
        name: "Rotterdam", flag: "🇳🇱", code: "NLRTM",
        lat: 51.9225, lon: 4.47917, berths: 45,
        metrics: { occupancy: 78, waiting: 11, avgWait: 14.2, medianWait: 11.8, traffic: 142 },
        forecast: [0.35, 0.48, 0.62, 0.78, 0.81],
        trend: [0.42, 0.38, 0.55, 0.61, 0.72, 0.78],
        vessels: [
            { name:"MSC ANNA", mmsi:"353712000", lat:51.82, lon:3.85, sog:14.2, cog:42, zone:"transit", dist:145, eta:"10h 12m", conf:62 },
            { name:"EVER GIVEN", mmsi:"353136000", lat:51.75, lon:4.10, sog:12.8, cog:38, zone:"approaching", dist:48, eta:"3h 45m", conf:88 },
            { name:"MAERSK SELETAR", mmsi:"219018102", lat:51.91, lon:4.38, sog:0.3, cog:0, zone:"anchor", dist:3.2, eta:"Waiting", conf:99 },
            { name:"CMA CGM MARCO POLO", mmsi:"228317600", lat:51.93, lon:4.45, sog:0.0, cog:0, zone:"berth", dist:0.1, eta:"Berthed", conf:99 },
            { name:"HMM ALGECIRAS", mmsi:"440464000", lat:51.68, lon:3.42, sog:16.1, cog:55, zone:"transit", dist:178, eta:"11h 03m", conf:55 },
            { name:"COSCO SHIPPING ARIES", mmsi:"477328500", lat:51.88, lon:4.25, sog:6.2, cog:70, zone:"approaching", dist:12, eta:"1h 56m", conf:95 },
            { name:"ONE APUS", mmsi:"353875000", lat:51.92, lon:4.42, sog:0.1, cog:0, zone:"anchor", dist:2.8, eta:"Waiting", conf:99 },
            { name:"MSC GULSUN", mmsi:"353154000", lat:51.93, lon:4.48, sog:0.0, cog:0, zone:"berth", dist:0.0, eta:"Berthed", conf:99 },
            { name:"HAPAG LLOYD EXPRESS", mmsi:"218424000", lat:51.78, lon:3.95, sog:11.5, cog:45, zone:"approaching", dist:38, eta:"3h 18m", conf:90 },
            { name:"YANG MING WARRANTY", mmsi:"416394000", lat:51.60, lon:3.10, sog:15.8, cog:48, zone:"transit", dist:192, eta:"12h 09m", conf:50 },
            { name:"PIL PALAWAN", mmsi:"563089100", lat:51.90, lon:4.40, sog:0.4, cog:12, zone:"anchor", dist:4.1, eta:"Waiting", conf:99 },
            { name:"ZIM INTEGRATED", mmsi:"428372000", lat:51.85, lon:4.18, sog:8.4, cog:60, zone:"approaching", dist:22, eta:"2h 37m", conf:92 },
        ],
    },
    SGSIN: {
        name: "Singapore", flag: "🇸🇬", code: "SGSIN",
        lat: 1.2644, lon: 103.8222, berths: 67,
        metrics: { occupancy: 91, waiting: 23, avgWait: 22.6, medianWait: 18.4, traffic: 287 },
        forecast: [0.72, 0.80, 0.85, 0.90, 0.88],
        trend: [0.65, 0.70, 0.75, 0.82, 0.88, 0.91],
        vessels: [
            { name:"EVERGREEN EVER ACE", mmsi:"353497000", lat:1.15, lon:103.70, sog:12.0, cog:30, zone:"approaching", dist:28, eta:"2h 20m", conf:92 },
            { name:"MSC IRINA", mmsi:"353875100", lat:1.10, lon:103.50, sog:14.5, cog:45, zone:"transit", dist:85, eta:"5h 52m", conf:75 },
            { name:"OOCL HONG KONG", mmsi:"477518200", lat:1.27, lon:103.82, sog:0.0, cog:0, zone:"berth", dist:0.0, eta:"Berthed", conf:99 },
            { name:"NYK VEGA", mmsi:"431501593", lat:1.24, lon:103.78, sog:0.2, cog:0, zone:"anchor", dist:2.5, eta:"Waiting", conf:99 },
        ],
    },
    CNSHA: {
        name: "Shanghai", flag: "🇨🇳", code: "CNSHA",
        lat: 31.2304, lon: 121.4737, berths: 52,
        metrics: { occupancy: 84, waiting: 16, avgWait: 18.5, medianWait: 15.2, traffic: 198 },
        forecast: [0.55, 0.60, 0.70, 0.75, 0.72],
        trend: [0.50, 0.55, 0.62, 0.68, 0.78, 0.84],
        vessels: [
            { name:"COSCO FORTUNE", mmsi:"477125300", lat:31.10, lon:121.30, sog:10.2, cog:20, zone:"approaching", dist:18, eta:"1h 46m", conf:94 },
            { name:"SITC BANGKOK", mmsi:"477901200", lat:31.22, lon:121.47, sog:0.0, cog:0, zone:"berth", dist:0.1, eta:"Berthed", conf:99 },
        ],
    },
    DEHAM: {
        name: "Hamburg", flag: "🇩🇪", code: "DEHAM",
        lat: 53.5461, lon: 9.9669, berths: 30,
        metrics: { occupancy: 62, waiting: 5, avgWait: 8.3, medianWait: 6.1, traffic: 78 },
        forecast: [0.20, 0.25, 0.30, 0.42, 0.38],
        trend: [0.30, 0.35, 0.28, 0.40, 0.50, 0.62],
        vessels: [
            { name:"HAPAG HAMBURG", mmsi:"218000001", lat:53.50, lon:9.80, sog:8.0, cog:90, zone:"approaching", dist:10, eta:"1h 15m", conf:96 },
        ],
    },
    USNYC: {
        name: "New York / New Jersey", flag: "🇺🇸", code: "USNYC",
        lat: 40.6892, lon: -74.0445, berths: 35,
        metrics: { occupancy: 71, waiting: 8, avgWait: 11.7, medianWait: 9.8, traffic: 95 },
        forecast: [0.30, 0.38, 0.52, 0.60, 0.55],
        trend: [0.45, 0.40, 0.48, 0.55, 0.62, 0.71],
        vessels: [
            { name:"ACL ATLANTIC SAIL", mmsi:"311000123", lat:40.55, lon:-73.85, sog:10.5, cog:350, zone:"approaching", dist:15, eta:"1h 26m", conf:94 },
            { name:"MAERSK IOWA", mmsi:"219018200", lat:40.30, lon:-73.50, sog:14.0, cog:340, zone:"transit", dist:82, eta:"5h 51m", conf:72 },
        ],
    },
};

const DATA_SOURCES = [
    { name:"AIS Vessel Positions", status:"active", freshness:"3 min ago", detail:"Hourly 5-min snapshots, 200nm radius", contribution: 42 },
    { name:"NOAA Weather", status:"active", freshness:"12 min ago", detail:"Wave height, wind speed, storm alerts", contribution: 22 },
    { name:"CMEMS Ocean Currents", status:"active", freshness:"1h ago", detail:"Surface current vectors, speed anomalies", contribution: 8 },
    { name:"UN Comtrade", status:"active", freshness:"6h ago", detail:"Monthly trade volumes by commodity", contribution: 12 },
    { name:"FRED Economics", status:"stale", freshness:"2 days ago", detail:"Consumer spending, manufacturing PMI", contribution: 6 },
    { name:"GDELT News", status:"active", freshness:"28 min ago", detail:"Port disruption mentions, canal events", contribution: 10 },
];

const FORECAST_LABELS = ["+1h", "+6h", "+12h", "+24h", "+48h"];
const TREND_LABELS = ["W-5", "W-4", "W-3", "W-2", "W-1", "Now"];

// ---------------------------------------------------------------------------
// STATE
// ---------------------------------------------------------------------------

let currentPort = "NLRTM";
let map, vesselMarkers = [], rangeCircles = [];
let forecastChart, trendChart;

// ---------------------------------------------------------------------------
// INIT
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    initPortDropdown();
    initMap();
    renderPort(currentPort);
});

// ---------------------------------------------------------------------------
// PORT SELECTOR
// ---------------------------------------------------------------------------

function initPortDropdown() {
    const dd = document.getElementById("port-dropdown");
    dd.innerHTML = Object.entries(PORTS).map(([key, p]) =>
        `<div class="port-option ${key === currentPort ? 'active' : ''}" data-port="${key}">
            <span class="po-flag">${p.flag}</span>
            <span class="po-name">${p.name}</span>
            <span class="po-code">${p.code}</span>
        </div>`
    ).join("");

    document.getElementById("port-selector-btn").addEventListener("click", () => {
        document.getElementById("port-selector").classList.toggle("open");
    });

    dd.querySelectorAll(".port-option").forEach(opt => {
        opt.addEventListener("click", () => {
            currentPort = opt.dataset.port;
            document.getElementById("port-selector").classList.remove("open");
            renderPort(currentPort);
        });
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest("#port-selector")) {
            document.getElementById("port-selector").classList.remove("open");
        }
    });

    document.querySelectorAll(".map-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".map-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const range = parseInt(btn.dataset.range);
            const p = PORTS[currentPort];
            const zoom = range === 200 ? 8 : range === 50 ? 10 : 12;
            map.setView([p.lat, p.lon], zoom, { animate: true });
        });
    });
}

// ---------------------------------------------------------------------------
// MAP
// ---------------------------------------------------------------------------

function initMap() {
    map = L.map("map", { zoomControl: true, attributionControl: true }).setView([51.9225, 4.47917], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© OpenStreetMap',
        maxZoom: 18,
    }).addTo(map);
}

function getVesselColor(zone) {
    return { berth: "#22c55e", anchor: "#f59e0b", approaching: "#3b82f6", transit: "#64748b" }[zone] || "#64748b";
}

function renderMap(portData) {
    vesselMarkers.forEach(m => map.removeLayer(m));
    rangeCircles.forEach(c => map.removeLayer(c));
    vesselMarkers = [];
    rangeCircles = [];

    map.setView([portData.lat, portData.lon], 8, { animate: true });

    [200, 50, 10].forEach(nm => {
        const meters = nm * 1852;
        const circle = L.circle([portData.lat, portData.lon], {
            radius: meters, color: "rgba(14,165,233,0.25)", fillColor: "transparent",
            weight: 1, dashArray: nm === 200 ? "8 4" : nm === 50 ? "4 4" : "2 2",
        }).addTo(map);
        rangeCircles.push(circle);

        const label = L.marker(
            [portData.lat + (nm * 0.0166), portData.lon],
            { icon: L.divIcon({ className: "", html: `<span style="color:#0ea5e9;font-size:11px;font-weight:600;font-family:Inter,sans-serif;text-shadow:0 0 4px rgba(0,0,0,0.8)">${nm}nm</span>`, iconSize: [40, 16] }) }
        ).addTo(map);
        rangeCircles.push(label);
    });

    // Port marker
    const portIcon = L.divIcon({
        className: "",
        html: `<div style="width:14px;height:14px;background:#0ea5e9;border:2px solid #fff;border-radius:3px;box-shadow:0 0 8px rgba(14,165,233,0.6)"></div>`,
        iconSize: [14, 14], iconAnchor: [7, 7],
    });
    vesselMarkers.push(L.marker([portData.lat, portData.lon], { icon: portIcon }).addTo(map));

    portData.vessels.forEach(v => {
        const color = getVesselColor(v.zone);
        const size = v.zone === "berth" || v.zone === "anchor" ? 8 : 10;
        const icon = L.divIcon({
            className: "",
            html: `<div style="width:${size}px;height:${size}px;background:${color};border-radius:50%;border:1.5px solid rgba(255,255,255,0.6);box-shadow:0 0 6px ${color}80"></div>`,
            iconSize: [size, size], iconAnchor: [size/2, size/2],
        });

        const marker = L.marker([v.lat, v.lon], { icon }).addTo(map);
        marker.bindPopup(`
            <div class="vessel-popup">
                <h3>${v.name}</h3>
                <div class="vp-row"><span>MMSI</span><span>${v.mmsi}</span></div>
                <div class="vp-row"><span>Speed</span><span>${v.sog} kts</span></div>
                <div class="vp-row"><span>Distance</span><span>${v.dist} nm</span></div>
                <div class="vp-row"><span>ETA</span><span>${v.eta}</span></div>
                <div class="vp-row"><span>Confidence</span><span>${v.conf}%</span></div>
            </div>
        `, { className: "vessel-popup-container" });
        vesselMarkers.push(marker);
    });
}

// ---------------------------------------------------------------------------
// RENDER ALL PANELS
// ---------------------------------------------------------------------------

function renderPort(portKey) {
    const p = PORTS[portKey];

    // Update nav
    document.getElementById("selected-port-flag").textContent = p.flag;
    document.getElementById("selected-port-name").textContent = p.name;
    document.querySelectorAll(".port-option").forEach(opt => {
        opt.classList.toggle("active", opt.dataset.port === portKey);
    });

    renderMap(p);
    renderMetrics(p);
    renderForecastChart(p);
    renderVesselsTable(p);
    renderTrendChart(p);
    renderSources();
}

// ---------------------------------------------------------------------------
// METRICS
// ---------------------------------------------------------------------------

function renderMetrics(p) {
    const m = p.metrics;
    const occColor = m.occupancy > 80 ? "var(--red)" : m.occupancy > 60 ? "var(--yellow)" : "var(--green)";
    const waitColor = m.avgWait > 16 ? "var(--red)" : m.avgWait > 10 ? "var(--yellow)" : "var(--green)";

    document.getElementById("metric-cards").innerHTML = `
        <div class="metric-card">
            <div class="metric-value" style="color:${occColor}">${m.occupancy}%</div>
            <div class="metric-label">Berth Occupancy</div>
            <div class="metric-sub metric-up">↑ +6% vs last week</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:var(--yellow)">${m.waiting}</div>
            <div class="metric-label">Vessels Waiting</div>
            <div class="metric-sub metric-up">↑ +3 vs last week</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${waitColor}">${m.avgWait}h</div>
            <div class="metric-label">Avg Wait Time</div>
            <div class="metric-sub metric-up">↑ +2.1h vs last week</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:var(--text-primary)">${m.medianWait}h</div>
            <div class="metric-label">Median Wait</div>
            <div class="metric-sub metric-neutral">~ stable</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:var(--accent)">${m.traffic}</div>
            <div class="metric-label">Weekly Traffic</div>
            <div class="metric-sub metric-down">↓ -5 vs last week</div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// FORECAST CHART
// ---------------------------------------------------------------------------

function getForecastColor(val) {
    if (val >= 0.7) return "#ef4444";
    if (val >= 0.45) return "#f59e0b";
    return "#22c55e";
}

function renderForecastChart(p) {
    const ctx = document.getElementById("forecast-chart").getContext("2d");
    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: FORECAST_LABELS,
            datasets: [{
                data: p.forecast.map(v => v * 100),
                backgroundColor: p.forecast.map(v => getForecastColor(v)),
                borderRadius: 4, borderSkipped: false, barPercentage: 0.6,
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: { label: (c) => `Congestion: ${c.raw.toFixed(0)}%` },
                    backgroundColor: "#1c1f2b", titleColor: "#f1f5f9", bodyColor: "#94a3b8",
                    borderColor: "rgba(148,163,184,0.15)", borderWidth: 1,
                },
            },
            scales: {
                x: { max: 100, grid: { color: "rgba(148,163,184,0.06)" }, ticks: { color: "#64748b", font: { size: 11 }, callback: v => v + "%" } },
                y: { grid: { display: false }, ticks: { color: "#94a3b8", font: { size: 12, weight: 600 } } },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// VESSELS TABLE
// ---------------------------------------------------------------------------

function renderVesselsTable(p) {
    document.getElementById("vessel-count").textContent = `${p.vessels.length} vessels tracked`;
    const tbody = document.getElementById("vessels-tbody");
    const zoneOrder = { berth: 0, anchor: 1, approaching: 2, transit: 3 };
    const sorted = [...p.vessels].sort((a, b) => zoneOrder[a.zone] - zoneOrder[b.zone]);

    tbody.innerHTML = sorted.map(v => {
        const confColor = v.conf >= 85 ? "var(--green)" : v.conf >= 65 ? "var(--yellow)" : "var(--red)";
        return `<tr>
            <td class="vessel-name">${v.name}</td>
            <td class="mmsi-val">${v.mmsi}</td>
            <td><span class="zone-badge zone-${v.zone}">${v.zone}</span></td>
            <td>${v.dist} nm</td>
            <td>${v.sog} kts</td>
            <td class="eta-val">${v.eta}</td>
            <td>
                <div class="confidence-bar">
                    <div class="conf-track"><div class="conf-fill" style="width:${v.conf}%;background:${confColor}"></div></div>
                    <span class="conf-label" style="color:${confColor}">${v.conf}%</span>
                </div>
            </td>
        </tr>`;
    }).join("");
}

// ---------------------------------------------------------------------------
// TREND CHART
// ---------------------------------------------------------------------------

function renderTrendChart(p) {
    const ctx = document.getElementById("trend-chart").getContext("2d");
    if (trendChart) trendChart.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 140);
    gradient.addColorStop(0, "rgba(14,165,233,0.25)");
    gradient.addColorStop(1, "rgba(14,165,233,0)");

    trendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: TREND_LABELS,
            datasets: [{
                data: p.trend.map(v => v * 100),
                borderColor: "#0ea5e9", backgroundColor: gradient,
                fill: true, tension: 0.4, pointRadius: 4,
                pointBackgroundColor: "#0ea5e9", pointBorderColor: "#1c1f2b", pointBorderWidth: 2,
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: { label: (c) => `Congestion: ${c.raw.toFixed(0)}%` },
                    backgroundColor: "#1c1f2b", titleColor: "#f1f5f9", bodyColor: "#94a3b8",
                    borderColor: "rgba(148,163,184,0.15)", borderWidth: 1,
                },
            },
            scales: {
                x: { grid: { color: "rgba(148,163,184,0.06)" }, ticks: { color: "#64748b", font: { size: 11 } } },
                y: { min: 0, max: 100, grid: { color: "rgba(148,163,184,0.06)" }, ticks: { color: "#64748b", font: { size: 11 }, callback: v => v + "%" } },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// DATA SOURCES
// ---------------------------------------------------------------------------

function renderSources() {
    document.getElementById("sources-grid").innerHTML = DATA_SOURCES.map(s => {
        const icon = s.status === "active" ? "✓" : s.status === "stale" ? "⚠" : "✗";
        return `<div class="source-card">
            <div class="source-top">
                <span class="source-name">${s.name}</span>
                <span class="source-status ${s.status}">${icon} ${s.status}</span>
            </div>
            <div class="source-details">${s.detail}</div>
            <div class="source-freshness">⏱ ${s.freshness}</div>
            <div class="source-contribution">
                <div class="contrib-bar-track"><div class="contrib-bar-fill" style="width:${s.contribution}%"></div></div>
                <span class="contrib-label">${s.contribution}%</span>
            </div>
        </div>`;
    }).join("");
}
