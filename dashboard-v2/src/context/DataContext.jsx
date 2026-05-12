import { createContext, useContext, useState, useEffect, useMemo } from 'react';

const DataContext = createContext(null);
const ZONE_ORDER = { berth: 0, anchor: 1, approaching: 2, transit: 3 };

// ── Derive readable labels from the export payload ─────────────────────────
// Falls back gracefully if labels are missing (older demo-data.js)
function getTrendLabels(labels) {
  return labels?.trend || ['6d ago', '5d ago', '4d ago', '3d ago', 'Yesterday', 'Today'];
}
function getOutlookLabels(labels) {
  return labels?.outlook || ['4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'];
}

function toNumber(value, fallback = 0) {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

function compareVessels(a, b) {
  const zoneDelta = (ZONE_ORDER[a.zone] ?? 99) - (ZONE_ORDER[b.zone] ?? 99);
  if (zoneDelta !== 0) return zoneDelta;

  const distanceDelta = toNumber(a.dist) - toNumber(b.dist);
  if (distanceDelta !== 0) return distanceDelta;

  return (a.name || '').localeCompare(b.name || '');
}

function buildDerivedSchedule(vessels) {
  return vessels
    .filter((vessel) => vessel.zone === 'approaching' || vessel.zone === 'transit')
    .sort((left, right) => toNumber(left.dist) - toNumber(right.dist))
    .map((vessel) => ({
      vessel: vessel.name,
      mmsi: vessel.mmsi,
      type: 'Arrival',
      status: vessel.zone === 'approaching' ? 'Approaching' : 'In Transit',
      eta: vessel.eta,
      distance_nm: toNumber(vessel.dist),
      zone: vessel.zone,
      sog: toNumber(vessel.sog),
    }));
}

function normalizePort(port) {
  if (!port) return port;

  const vessels = Array.isArray(port.vessels)
    ? [...port.vessels].sort(compareVessels)
    : [];

  const trackedFromVessels = vessels.length;
  const waiting = vessels.filter((vessel) => vessel.zone === 'anchor').length;
  const berthed = vessels.filter((vessel) => vessel.zone === 'berth').length;
  const avgSpeed = trackedFromVessels
    ? Number(
        (
          vessels.reduce((sum, vessel) => sum + toNumber(vessel.sog), 0) / trackedFromVessels
        ).toFixed(1)
      )
    : toNumber(port.metrics?.avgSpeed);
  const derivedCongestionPct = berthed + waiting > 0
    ? Math.round((waiting / (berthed + waiting)) * 100)
    : toNumber(port.metrics?.congestionPct);
  const schedule = buildDerivedSchedule(vessels);

  return {
    ...port,
    vessels,
    schedule,
    metrics: {
      ...port.metrics,
      tracked: Math.max(toNumber(port.metrics?.tracked), trackedFromVessels),
      waiting,
      avgSpeed,
      congestionPct: waiting > 0 ? derivedCongestionPct : toNumber(port.metrics?.congestionPct),
      maxWave: toNumber(port.metrics?.maxWave),
    },
  };
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

// VITE_DATA_URL  → set in Vercel env vars to your CloudFront JSON URL
//   e.g. https://d1234.cloudfront.net/api/v1/demo-data.json
// Unset in local dev → falls back to window.DEMO_DATA (public/demo-data.js fixture)
const CLOUD_DATA_URL = import.meta.env.VITE_DATA_URL ?? null;

async function loadCloudData() {
  if (!CLOUD_DATA_URL) throw new Error('No VITE_DATA_URL configured');
  const raw = await fetchJson(CLOUD_DATA_URL);
  if (!raw?.ports) throw new Error('Unexpected shape from cloud data URL');
  return raw;
}

async function loadLivePorts() {
  // In production (Vercel) fetch directly from CloudFront — single request, no CORS issue.
  if (CLOUD_DATA_URL) return loadCloudData();

  const apiBases = ['/api', 'http://localhost:8000/api'];
  let lastError = null;

  for (const base of apiBases) {
    try {
      const ports = await fetchJson(`${base}/ports`);
      const portEntries = await Promise.all(
        Object.keys(ports).map(async (code) => [code, await fetchJson(`${base}/ports/${code}`)])
      );
      const normalizedPorts = Object.fromEntries(
        portEntries.map(([code, port]) => [code, normalizePort(port)])
      );
      const totalSurfaced = Object.values(normalizedPorts).reduce(
        (sum, port) => sum + (port.vessels?.length ?? 0),
        0
      );
      if (totalSurfaced === 0) {
        throw new Error('Live API returned no surfaced vessels');
      }

      return {
        metadata: {
          generatedAt: new Date().toISOString(),
          mode: 'live-api',
        },
        labels: {
          outlook: ['D-4', 'D-3', 'D-2', 'D-1', 'Now'],
          trend: ['D-5', 'D-4', 'D-3', 'D-2', 'D-1', 'Now'],
        },
        sources: [],
        ports: normalizedPorts,
      };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error('Live API unavailable');
}

export function DataProvider({ children }) {
  const [data, setData] = useState(null);
  const [currentPortCode, setCurrentPortCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const liveData = await loadLivePorts();
        if (cancelled) return;
        setData(liveData);
        setCurrentPortCode(Object.keys(liveData.ports)[0] ?? null);
        setError(null);
        return;
      } catch {
        // Fall back to the demo artifact when the local API is not running.
      }

      const raw = window.DEMO_DATA;
      if (!raw || !raw.ports) {
        if (!cancelled) {
          setError('No live API or demo-data.js found. Start the API or regenerate dashboard/demo-data.js and copy it to dashboard-v2/public/demo-data.js.');
        }
        return;
      }

      if (cancelled) return;
      const normalized = {
        ...raw,
        ports: Object.fromEntries(
          Object.entries(raw.ports).map(([code, port]) => [code, normalizePort(port)])
        ),
      };
      setData(normalized);
      setCurrentPortCode(Object.keys(normalized.ports)[0] ?? null);
      setError(null);
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  const port = useMemo(() => {
    if (!data || !currentPortCode) return null;
    return data.ports[currentPortCode] ?? null;
  }, [data, currentPortCode]);

  const ports = useMemo(() => data?.ports ?? {}, [data]);

  if (!data && error) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 text-on-surface px-6">
        <span className="material-symbols-outlined text-error text-5xl">error</span>
        <p className="font-title-sm text-on-surface text-center">No data available</p>
        <p className="font-body-sm text-on-surface-variant text-center max-w-md">{error}</p>
      </div>
    );
  }

  if (!data || !currentPortCode) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-on-surface-variant font-body-md">
        Loading…
      </div>
    );
  }

  const value = {
    // Core port data
    port,
    ports,
    currentPortCode,
    setCurrentPortCode,
    // Export metadata
    metadata: data.metadata,
    sources: data.sources ?? [],
    trendLabels: getTrendLabels(data.labels),
    outlookLabels: getOutlookLabels(data.labels),
  };

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useData() {
  const context = useContext(DataContext);
  if (!context) throw new Error('useData must be used within a DataProvider');
  return context;
}
