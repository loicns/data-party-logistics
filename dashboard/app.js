const FALLBACK_DATA = {
    ports: {
        NLRTM: {
            name: "Rotterdam",
            flag: "NL",
            code: "NLRTM",
            lat: 51.9225,
            lon: 4.4792,
            metrics: {
                congestionPct: 0,
                waiting: 0,
                avgSpeed: 0,
                maxWave: 0,
                tracked: 0,
            },
            forecast: [0, 0, 0, 0, 0],
            trend: [0, 0, 0, 0, 0, 0],
            vessels: [],
        },
    },
    sources: [
        {
            name: "AIS Vessel Positions",
            status: "stale",
            freshness: "unavailable",
            detail: "No exported dashboard data found",
            contribution: 55,
        },
        {
            name: "Marine Weather",
            status: "stale",
            freshness: "unavailable",
            detail: "No exported dashboard data found",
            contribution: 30,
        },
    ],
    labels: {
        outlook: ["D-4", "D-3", "D-2", "D-1", "Now"],
        trend: ["D-5", "D-4", "D-3", "D-2", "D-1", "Now"],
    },
    metadata: {
        generatedAt: "Unavailable",
        mode: "fallback",
    },
};

const APP_DATA = window.DEMO_DATA || FALLBACK_DATA;
const PORTS = APP_DATA.ports;
const DATA_SOURCES = APP_DATA.sources;
const FORECAST_LABELS = APP_DATA.labels.outlook;
const TREND_LABELS = APP_DATA.labels.trend;

let currentPort = Object.keys(PORTS)[0];
let activeView = "overview";
let activeRange = 200;
let map;
let vesselMarkers = [];
let rangeCircles = [];
let forecastChart;
let trendChart;

document.addEventListener("DOMContentLoaded", () => {
    initPortDropdown();
    initViewTabs();
    initMapShell();
    initMap();
    renderPort(currentPort);
    switchView(activeView);
});

function initPortDropdown() {
    const dropdown = document.getElementById("port-dropdown");
    dropdown.innerHTML = Object.entries(PORTS)
        .map(
            ([key, port]) => `
            <div class="port-option ${key === currentPort ? "active" : ""}" data-port="${key}">
                <span class="po-flag">${port.flag}</span>
                <span class="po-name">${port.name}</span>
                <span class="po-code">${port.code}</span>
            </div>
        `,
        )
        .join("");

    document.getElementById("port-selector-btn").addEventListener("click", () => {
        document.getElementById("port-selector").classList.toggle("open");
    });

    dropdown.querySelectorAll(".port-option").forEach((option) => {
        option.addEventListener("click", () => {
            currentPort = option.dataset.port;
            document.getElementById("port-selector").classList.remove("open");
            renderPort(currentPort);
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("#port-selector")) {
            document.getElementById("port-selector").classList.remove("open");
        }
    });
}

function initViewTabs() {
    document.querySelectorAll(".view-tab").forEach((button) => {
        button.addEventListener("click", () => {
            switchView(button.dataset.view);
        });
    });
}

function initMapShell() {
    document.querySelectorAll(".map-btn").forEach((button) => {
        button.addEventListener("click", () => {
            activeRange = parseInt(button.dataset.range, 10);
            document.querySelectorAll(".map-btn").forEach((candidate) => {
                candidate.classList.toggle("active", candidate === button);
            });
            updateMapRange();
        });
    });
}

function mountMapShell() {
    const shell = document.getElementById("map-shell");
    const targetId = activeView === "map" ? "map-view-slot" : "overview-map-slot";
    const target = document.getElementById(targetId);

    if (shell.parentElement !== target) {
        target.appendChild(shell);
    }

    shell.classList.add("mounted");

    if (map) {
        setTimeout(() => map.invalidateSize(), 0);
    }
}

function switchView(viewName) {
    activeView = viewName;

    document.querySelectorAll(".view-tab").forEach((button) => {
        button.classList.toggle("active", button.dataset.view === viewName);
    });

    document.querySelectorAll(".view").forEach((view) => {
        view.classList.toggle("active", view.id === `${viewName}-view`);
    });

    mountMapShell();
    updateMapRange();
}

function initMap() {
    map = L.map("map", { zoomControl: true, attributionControl: true }).setView(
        [51.9225, 4.4792],
        8,
    );

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 18,
    }).addTo(map);
}

function getVesselColor(zone) {
    return {
        berth: "#22c55e",
        anchor: "#f59e0b",
        approaching: "#3b82f6",
        transit: "#64748b",
    }[zone] || "#64748b";
}

function updateMapRange() {
    const port = PORTS[currentPort];
    const zoom = activeRange === 200 ? 8 : activeRange === 50 ? 10 : 12;

    if (map && port) {
        map.setView([port.lat, port.lon], zoom, { animate: true });
    }

    document.getElementById("map-radius-label").textContent = `${activeRange}nm`;
}

function renderMap(portData) {
    vesselMarkers.forEach((marker) => map.removeLayer(marker));
    rangeCircles.forEach((circle) => map.removeLayer(circle));
    vesselMarkers = [];
    rangeCircles = [];

    updateMapRange();

    [200, 50, 10].forEach((nm) => {
        const meters = nm * 1852;
        const circle = L.circle([portData.lat, portData.lon], {
            radius: meters,
            color: "rgba(14,165,233,0.25)",
            fillColor: "transparent",
            weight: 1,
            dashArray: nm === 200 ? "8 4" : nm === 50 ? "4 4" : "2 2",
        }).addTo(map);
        rangeCircles.push(circle);

        const label = L.marker([portData.lat + nm * 0.0166, portData.lon], {
            icon: L.divIcon({
                className: "",
                html: `<span style="color:#0ea5e9;font-size:11px;font-weight:600;font-family:Inter,sans-serif;text-shadow:0 0 4px rgba(0,0,0,0.8)">${nm}nm</span>`,
                iconSize: [40, 16],
            }),
        }).addTo(map);
        rangeCircles.push(label);
    });

    const portIcon = L.divIcon({
        className: "",
        html: `<div style="width:14px;height:14px;background:#0ea5e9;border:2px solid #fff;border-radius:3px;box-shadow:0 0 8px rgba(14,165,233,0.6)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
    });
    vesselMarkers.push(L.marker([portData.lat, portData.lon], { icon: portIcon }).addTo(map));

    portData.vessels.forEach((vessel) => {
        const color = getVesselColor(vessel.zone);
        const size = vessel.zone === "berth" || vessel.zone === "anchor" ? 8 : 10;
        const icon = L.divIcon({
            className: "",
            html: `<div style="width:${size}px;height:${size}px;background:${color};border-radius:50%;border:1.5px solid rgba(255,255,255,0.6);box-shadow:0 0 6px ${color}80"></div>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
        });

        const marker = L.marker([vessel.lat, vessel.lon], { icon }).addTo(map);
        marker.bindPopup(
            `
            <div class="vessel-popup">
                <h3>${vessel.name}</h3>
                <div class="vp-row"><span>MMSI</span><span>${vessel.mmsi}</span></div>
                <div class="vp-row"><span>Speed</span><span>${vessel.sog} kts</span></div>
                <div class="vp-row"><span>Distance</span><span>${vessel.dist} nm</span></div>
                <div class="vp-row"><span>ETA</span><span>${vessel.eta}</span></div>
                <div class="vp-row"><span>Confidence</span><span>${vessel.conf}%</span></div>
            </div>
        `,
            { className: "vessel-popup-container" },
        );
        vesselMarkers.push(marker);
    });
}

function renderPort(portKey) {
    const port = PORTS[portKey];

    document.getElementById("last-update").textContent = `Updated ${APP_DATA.metadata.generatedAt}`;
    document.getElementById("selected-port-flag").textContent = port.flag;
    document.getElementById("selected-port-name").textContent = port.name;
    document.getElementById("map-port-label").textContent = port.name;
    document.getElementById("map-tracked-label").textContent = String(port.metrics.tracked);
    document.getElementById("data-mode-label").textContent = APP_DATA.metadata.mode.replace("-", " ");
    document.getElementById("export-mode-copy").textContent =
        `This page is currently powered by a ${APP_DATA.metadata.mode.replace("-", " ")} generated at ${APP_DATA.metadata.generatedAt}.`;

    document.querySelectorAll(".port-option").forEach((option) => {
        option.classList.toggle("active", option.dataset.port === portKey);
    });

    renderMap(port);
    renderMetrics(port);
    renderSummary(port);
    renderForecastChart(port);
    renderVesselsTable(port);
    renderTrendChart(port);
    renderSources();
    renderHealth();
}

function renderMetrics(port) {
    const metrics = port.metrics;
    const congestionColor =
        metrics.congestionPct >= 70
            ? "var(--red)"
            : metrics.congestionPct >= 45
              ? "var(--yellow)"
              : "var(--green)";
    const speedColor =
        metrics.avgSpeed <= 2
            ? "var(--red)"
            : metrics.avgSpeed <= 6
              ? "var(--yellow)"
              : "var(--green)";
    const waveColor =
        metrics.maxWave >= 3
            ? "var(--red)"
            : metrics.maxWave >= 1.5
              ? "var(--yellow)"
              : "var(--green)";

    document.getElementById("metric-cards").innerHTML = `
        <div class="metric-card">
            <div class="metric-value" style="color:${congestionColor}">${metrics.congestionPct}%</div>
            <div class="metric-label">Congestion Score</div>
            <div class="metric-sub metric-neutral">latest mart snapshot</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:var(--yellow)">${metrics.waiting}</div>
            <div class="metric-label">Anchored Vessels</div>
            <div class="metric-sub metric-neutral">waiting near port</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${speedColor}">${metrics.avgSpeed}</div>
            <div class="metric-label">Avg Speed In Zone</div>
            <div class="metric-sub metric-neutral">knots</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${waveColor}">${metrics.maxWave}</div>
            <div class="metric-label">Max Wave Height</div>
            <div class="metric-sub metric-neutral">meters</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:var(--accent)">${metrics.tracked}</div>
            <div class="metric-label">Tracked Vessels</div>
            <div class="metric-sub metric-neutral">latest daily total</div>
        </div>
    `;
}

function renderSummary(port) {
    const metrics = port.metrics;
    const isHighRisk = metrics.congestionPct >= 70 || metrics.waiting >= 8 || metrics.maxWave >= 3;
    const isMediumRisk =
        !isHighRisk && (metrics.congestionPct >= 45 || metrics.waiting >= 3 || metrics.maxWave >= 1.5);

    const headline = isHighRisk
        ? "Port risk is elevated right now"
        : isMediumRisk
          ? "Port risk is building"
          : "Port risk is low right now";

    const reasons = [];
    if (metrics.waiting > 0) {
        reasons.push(`${metrics.waiting} anchored vessels near port`);
    }
    if (metrics.avgSpeed > 0) {
        reasons.push(`average in-zone speed ${metrics.avgSpeed} knots`);
    }
    if (metrics.maxWave > 0) {
        reasons.push(`max wave height ${metrics.maxWave}m`);
    }
    if (!reasons.length) {
        reasons.push("limited signal in current export");
    }

    document.getElementById("summary-kicker").textContent = `Monitoring ${port.name}`;
    document.getElementById("summary-headline").textContent = headline;
    document.getElementById("summary-copy").textContent =
        "This view keeps the highest-signal operational facts together before you drill into map details or source diagnostics.";
    document.getElementById("summary-reasons").innerHTML = reasons
        .map((reason) => `<span class="reason-chip">${reason}</span>`)
        .join("");
}

function getForecastColor(value) {
    if (value >= 0.7) return "#ef4444";
    if (value >= 0.45) return "#f59e0b";
    return "#22c55e";
}

function renderForecastChart(port) {
    const context = document.getElementById("forecast-chart").getContext("2d");
    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(context, {
        type: "bar",
        data: {
            labels: FORECAST_LABELS,
            datasets: [
                {
                    data: port.forecast.map((value) => value * 100),
                    backgroundColor: port.forecast.map((value) => getForecastColor(value)),
                    borderRadius: 4,
                    borderSkipped: false,
                    barPercentage: 0.6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Congestion: ${context.raw.toFixed(0)}%`,
                    },
                    backgroundColor: "#1c1f2b",
                    titleColor: "#f1f5f9",
                    bodyColor: "#94a3b8",
                    borderColor: "rgba(148,163,184,0.15)",
                    borderWidth: 1,
                },
            },
            scales: {
                x: {
                    max: 100,
                    grid: { color: "rgba(148,163,184,0.06)" },
                    ticks: {
                        color: "#64748b",
                        font: { size: 11 },
                        callback: (value) => `${value}%`,
                    },
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#94a3b8", font: { size: 12, weight: 600 } },
                },
            },
        },
    });
}

function renderVesselsTable(port) {
    const emptyState = document.getElementById("vessel-empty-state");
    document.getElementById("vessel-count").textContent = `${port.vessels.length} vessels tracked`;
    const tbody = document.getElementById("vessels-tbody");

    if (!port.vessels.length) {
        emptyState.classList.add("active");
        tbody.innerHTML = "";
        return;
    }

    emptyState.classList.remove("active");
    const zoneOrder = { berth: 0, anchor: 1, approaching: 2, transit: 3 };
    const sorted = [...port.vessels].sort((left, right) => zoneOrder[left.zone] - zoneOrder[right.zone]);

    tbody.innerHTML = sorted
        .map((vessel) => {
            const confidenceColor =
                vessel.conf >= 85 ? "var(--green)" : vessel.conf >= 65 ? "var(--yellow)" : "var(--red)";

            return `
                <tr>
                    <td class="vessel-name">${vessel.name}</td>
                    <td class="mmsi-val">${vessel.mmsi}</td>
                    <td><span class="zone-badge zone-${vessel.zone}">${vessel.zone}</span></td>
                    <td>${vessel.dist} nm</td>
                    <td>${vessel.sog} kts</td>
                    <td class="eta-val">${vessel.eta}</td>
                    <td>
                        <div class="confidence-bar">
                            <div class="conf-track"><div class="conf-fill" style="width:${vessel.conf}%;background:${confidenceColor}"></div></div>
                            <span class="conf-label" style="color:${confidenceColor}">${vessel.conf}%</span>
                        </div>
                    </td>
                </tr>
            `;
        })
        .join("");
}

function renderTrendChart(port) {
    const context = document.getElementById("trend-chart").getContext("2d");
    if (trendChart) trendChart.destroy();

    const gradient = context.createLinearGradient(0, 0, 0, 140);
    gradient.addColorStop(0, "rgba(14,165,233,0.25)");
    gradient.addColorStop(1, "rgba(14,165,233,0)");

    trendChart = new Chart(context, {
        type: "line",
        data: {
            labels: TREND_LABELS,
            datasets: [
                {
                    data: port.trend.map((value) => value * 100),
                    borderColor: "#0ea5e9",
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: "#0ea5e9",
                    pointBorderColor: "#1c1f2b",
                    pointBorderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Congestion: ${context.raw.toFixed(0)}%`,
                    },
                    backgroundColor: "#1c1f2b",
                    titleColor: "#f1f5f9",
                    bodyColor: "#94a3b8",
                    borderColor: "rgba(148,163,184,0.15)",
                    borderWidth: 1,
                },
            },
            scales: {
                x: {
                    grid: { color: "rgba(148,163,184,0.06)" },
                    ticks: { color: "#64748b", font: { size: 11 } },
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: "rgba(148,163,184,0.06)" },
                    ticks: {
                        color: "#64748b",
                        font: { size: 11 },
                        callback: (value) => `${value}%`,
                    },
                },
            },
        },
    });
}

function renderSources() {
    document.getElementById("sources-grid").innerHTML = DATA_SOURCES.map((source) => {
        const icon = source.status === "active" ? "✓" : source.status === "stale" ? "!" : "×";
        return `
            <div class="source-card">
                <div class="source-top">
                    <span class="source-name">${source.name}</span>
                    <span class="source-status ${source.status}">${icon} ${source.status}</span>
                </div>
                <div class="source-details">${source.detail}</div>
                <div class="source-freshness">Updated ${source.freshness}</div>
                <div class="source-contribution">
                    <div class="contrib-bar-track"><div class="contrib-bar-fill" style="width:${source.contribution}%"></div></div>
                    <span class="contrib-label">${source.contribution}%</span>
                </div>
            </div>
        `;
    }).join("");
}

function renderHealth() {
    document.getElementById("health-grid").innerHTML = DATA_SOURCES.map((source) => `
        <div class="health-card">
            <div class="health-top">
                <span class="health-name">${source.name}</span>
                <span class="health-pill ${source.status}">${source.status}</span>
            </div>
            <div class="health-freshness">${source.freshness}</div>
            <div class="health-detail">${source.detail}</div>
        </div>
    `).join("");
}
