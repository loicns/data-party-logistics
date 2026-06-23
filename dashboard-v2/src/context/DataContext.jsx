import { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { PORT_COVERAGE, buildBerthAllocations } from '../data/portCoverage';

const DataContext = createContext(null);
const ZONE_ORDER = { berth: 0, anchor: 1, approaching: 2, transit: 3 };
const FETCH_TIMEOUT_MS = 6000;

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

function normalizeAisDiagnostics(port) {
  if (port.aisDiagnostics) return port.aisDiagnostics;
  if (!port.aisCoverageStatus) return null;

  return {
    status: port.aisCoverageStatus,
    message: port.aisCoverageMessage ?? 'No AIS messages received from provider.',
    detail: port.aisCoverageDetail ?? null,
    latestMessageWithin50nm: null,
    latestMessageWithin200nm: null,
    messageCountWithin50nm: 0,
    messageCountWithin200nm: 0,
    providerMessageCount: 0,
    nearestDistanceNm: null,
    secondSourceValidation: port.secondSourceValidation ?? 'recommended',
  };
}

function normalizePort(port) {
  if (!port) return port;

  const vessels = Array.isArray(port.vessels)
    ? [...port.vessels].sort(compareVessels)
    : [];

  // The export computes metrics from the FULL vessel set, then caps the
  // serialized list (vesselsTotal carries the real count). Backend metrics
  // are therefore authoritative; we only derive from the list as a fallback
  // for older exports that lacked these fields.
  const m = port.metrics ?? {};
  const derivedWaiting = vessels.filter((vessel) => vessel.zone === 'anchor').length;
  const derivedBerthed = vessels.filter((vessel) => vessel.zone === 'berth').length;
  const derivedAvgSpeed = vessels.length
    ? Number(
        (vessels.reduce((sum, vessel) => sum + toNumber(vessel.sog), 0) / vessels.length).toFixed(1)
      )
    : 0;
  const schedule = buildDerivedSchedule(vessels);

  return {
    ...port,
    vessels,
    vesselsTotal: toNumber(port.vesselsTotal, vessels.length),
    aisDiagnostics: normalizeAisDiagnostics(port),
    hasSnapshot: port.hasSnapshot ?? true,
    berthAllocations: buildBerthAllocations(port.code, port.berthAllocations),
    schedule,
    metrics: {
      ...m,
      tracked: toNumber(m.tracked, vessels.length),
      waiting: toNumber(m.waiting, derivedWaiting),
      berthed: toNumber(m.berthed, derivedBerthed),
      avgSpeed: toNumber(m.avgSpeed, derivedAvgSpeed),
      congestionPct: toNumber(m.congestionPct),
      maxWave: toNumber(m.maxWave),
    },
  };
}

function buildCoveragePort(code, meta) {
  return normalizePort({
    ...meta,
    code,
    metrics: {
      congestionPct: 0,
      waiting: 0,
      berthed: 0,
      avgSpeed: 0,
      maxWave: 0,
      tracked: 0,
    },
    forecast: [],
    trend: [],
    vessels: [],
    vesselsTotal: 0,
    berthAllocations: buildBerthAllocations(code),
    hasSnapshot: false,
  });
}

function normalizePorts(rawPorts = {}) {
  const coveragePorts = Object.fromEntries(
    Object.entries(PORT_COVERAGE).map(([code, meta]) => [code, buildCoveragePort(code, meta)])
  );

  const exportedPorts = Object.fromEntries(
    Object.entries(rawPorts).map(([code, port]) => [
      code,
      normalizePort({
        ...(PORT_COVERAGE[code] ?? {}),
        ...port,
        code: port.code ?? code,
        hasSnapshot: true,
      }),
    ])
  );

  return {
    ...coveragePorts,
    ...exportedPorts,
  };
}

// Parse a payload that is either plain JSON or a `window.DEMO_DATA = {...};`
// script. The export writes both a .json (for this fetch path) and a .js (the
// offline fallback); tolerating the JS wrapper here means a URL accidentally
// pointed at demo-data.js still works instead of silently falling back to the
// stale bundled fixture.
function parseDataPayload(text) {
  try {
    return JSON.parse(text);
  } catch (jsonError) {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start === -1 || end === -1 || end <= start) {
      throw new Error('Response is neither JSON nor a window.DEMO_DATA script', {
        cause: jsonError,
      });
    }
    return JSON.parse(text.slice(start, end + 1));
  }
}

// One retry with backoff: a transient CloudFront/network blip should not
// blank the whole dashboard.
async function fetchJson(url, retries = 1) {
  for (let attempt = 0; ; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      return parseDataPayload(await response.text());
    } catch (error) {
      if (attempt >= retries) throw error;
      await new Promise((resolve) => setTimeout(resolve, 1500 * (attempt + 1)));
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

// VITE_DATA_URL  → set in Vercel env vars to your CloudFront JSON URL
//   e.g. https://d1234.cloudfront.net/api/v1/demo-data.json
// Unset in local dev → use the Vite /live-data.json proxy, then fall back to
// window.DEMO_DATA only if live data is unavailable.
//
// Cross-origin CloudFront URLs are rewritten to same-origin proxy paths
// (/live-data.json or /live-data.js). CloudFront may not send CORS headers, so
// direct browser fetches from localhost can fail and silently fall back to the
// bundled fixture. Vercel handles the proxy in production; Vite handles it in
// local dev.
function resolveDataUrl() {
  const configured = import.meta.env.VITE_DATA_URL ?? null;
  if (!configured) return import.meta.env.DEV ? '/live-data.json' : null;
  if (typeof window === 'undefined') return configured;
  try {
    const target = new URL(configured, window.location.origin);
    if (target.origin !== window.location.origin) {
      return target.pathname.endsWith('.json') ? '/live-data.json' : '/live-data.js';
    }
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn(`Ignoring invalid VITE_DATA_URL: ${formatError(error)}`);
    }
  }
  return configured;
}

const CLOUD_DATA_URL = resolveDataUrl();

function normalizeDemoData(raw) {
  return {
    ...raw,
    ports: normalizePorts(raw.ports),
  };
}

async function loadCloudData() {
  if (!CLOUD_DATA_URL) throw new Error('No VITE_DATA_URL configured');
  const raw = await fetchJson(CLOUD_DATA_URL);
  if (!raw?.ports) throw new Error('Unexpected shape from cloud data URL');
  return normalizeDemoData(raw);
}

async function loadLivePorts() {
  // In production this is the same-origin /live-data.json Vercel proxy (no CORS);
  // in local dev it's the direct CloudFront URL from VITE_DATA_URL.
  if (CLOUD_DATA_URL) return loadCloudData();

  const apiBases = ['/api', 'http://localhost:8000/api'];
  let lastError = null;

  for (const base of apiBases) {
    try {
      const ports = await fetchJson(`${base}/ports`);
      const portEntries = await Promise.all(
        Object.keys(ports).map(async (code) => [code, await fetchJson(`${base}/ports/${code}`)])
      );
      const normalizedPorts = normalizePorts(Object.fromEntries(portEntries));
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

function formatError(error) {
  if (error instanceof Error) return error.message;
  return String(error);
}

export function DataProvider({ children }) {
  const [data, setData] = useState(null);
  const [currentPortCode, setCurrentPortCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let seededDemoData = false;

    async function loadData() {
      const demoData = window.DEMO_DATA;
      if (demoData?.ports && !seededDemoData) {
        const normalized = normalizeDemoData(demoData);
        seededDemoData = true;
        setData(normalized);
        setCurrentPortCode((prev) => prev ?? Object.keys(normalized.ports)[0] ?? null);
        setError(null);
      }

      if (!CLOUD_DATA_URL && demoData?.ports) {
        return;
      }

      try {
        const liveData = await loadLivePorts();
        if (cancelled) return;
        setData(liveData);
        setCurrentPortCode((prev) => prev ?? Object.keys(liveData.ports)[0] ?? null);
        setError(null);
        return;
      } catch (liveError) {
        if (!demoData || !demoData.ports) {
          if (!cancelled) {
            setError(`No live API or demo-data.js found. Start the API or restore dashboard-v2/public/demo-data.js. Last live-data error: ${formatError(liveError)}`);
          }
          return;
        }

        if (cancelled) return;
        const normalized = normalizeDemoData(demoData);
        setData(normalized);
        setCurrentPortCode((prev) => prev ?? Object.keys(normalized.ports)[0] ?? null);
        setError(null);
      }
    }

    loadData();

    // Re-fetch every 10 minutes so an open tab picks up the hourly export
    // without a manual reload.
    const interval = setInterval(loadData, 10 * 60 * 1000);

    return () => {
      cancelled = true;
      clearInterval(interval);
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
