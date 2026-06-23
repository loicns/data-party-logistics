import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../context/DataContext';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { installTransparentMissingImageHandler } from '../utils/mapLibreImages';

// How many vessels to preview on the dashboard before linking out to the full
// Traffic map. Keeps the card scannable instead of a long internal scroll.
const PREVIEW_COUNT = 6;

function hasProviderCoverageIssue(port) {
  return ['coverage_limited', 'no_provider_messages'].includes(port?.aisDiagnostics?.status);
}

function formatDiagnosticValue(value) {
  return value ?? 'None';
}

export default function OperationsDashboard() {
  const { port, metadata } = useData();
  const mapContainer = useRef(null);
  const map = useRef(null);

  useEffect(() => {
    if (map.current || !port) return; // initialize map only once

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/dark",
      center: [port.lon, port.lat],
      zoom: 10,
      attributionControl: false
    });
    installTransparentMissingImageHandler(map.current);

    map.current.on('load', () => {
      // Add markers for vessels
      port.vessels.forEach(vessel => {
        const el = document.createElement('div');
        el.className = 'w-3 h-3 rounded-full border border-background shadow-sm';
        if (vessel.zone === 'berth') el.style.backgroundColor = '#2dd96f';
        else if (vessel.zone === 'anchor') el.style.backgroundColor = '#f7b23b';
        else if (vessel.zone === 'approaching') el.style.backgroundColor = '#1ea7ff';
        else el.style.backgroundColor = '#7f8ea6';

        new maplibregl.Marker({ element: el })
          .setLngLat([vessel.lon, vessel.lat])
          .setPopup(new maplibregl.Popup({ offset: 10 }).setHTML(`<div class="text-on-surface bg-surface font-body-sm p-1">${vessel.name}</div>`))
          .addTo(map.current);
      });
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [port]);

  if (!port) return null;
  const m = port.metrics;
  const aisDiagnostics = port.aisDiagnostics;
  const providerCoverageIssue = hasProviderCoverageIssue(port);

  // Derived, data-bound values — no hardcoded gauge widths or fixed severity.
  const previewVessels = port.vessels.slice(0, PREVIEW_COUNT);
  const hiddenCount = Math.max(port.vessels.length - PREVIEW_COUNT, 0);
  const trackedDisplay = providerCoverageIssue && m.tracked === 0 ? '--' : m.tracked;
  const trackedLabel = providerCoverageIssue && m.tracked === 0 ? 'provider data' : 'active';
  const berthedShare = m.tracked > 0 && !providerCoverageIssue ? Math.round((m.berthed / m.tracked) * 100) : 0;
  const wavePct = Math.min((m.maxWave / 5) * 100, 100); // 5m ≈ full scale
  const anchorSeverity =
    m.waiting === 0
      ? { label: 'No vessels waiting', color: 'text-secondary', icon: 'check_circle', bar: 'bg-secondary' }
      : m.waiting >= 10
        ? { label: 'High congestion', color: 'text-error', icon: 'warning', bar: 'bg-error' }
        : { label: 'Moderate queue', color: 'text-tertiary', icon: 'info', bar: 'bg-tertiary' };

  return (
    <>
      <div className="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="font-display-lg text-display-lg text-on-surface mb-1">Live Operations</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">Real-time terminal congestion and vessel status.</p>
        </div>
        <div className="flex items-center gap-2 text-on-surface-variant bg-surface-container px-3 py-1.5 rounded-lg border border-outline-variant/30 font-data-mono text-data-mono shadow-sm">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          Live Sync: {metadata.generatedAt}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Metric 1 */}
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden group shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant truncate">TRACKED</span>
              <span className="material-symbols-outlined text-primary text-[20px]">directions_boat</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display-lg text-display-lg text-on-surface">{trackedDisplay}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">{trackedLabel}</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-on-surface-variant font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[14px]">
                {providerCoverageIssue ? 'cell_tower' : 'anchor'}
              </span>
              <span className="truncate">
                {providerCoverageIssue ? aisDiagnostics.message : `${m.berthed} berthed · ${m.waiting} waiting`}
              </span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className="h-full bg-primary" style={{ width: `${berthedShare}%` }}></div>
            </div>
          </div>
          {/* Metric 2 */}
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant truncate">CONGESTION</span>
              <span className="material-symbols-outlined text-tertiary text-[20px]">traffic</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display-lg text-display-lg text-on-surface">{m.congestionPct}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">%</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-on-surface-variant font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[14px]">horizontal_rule</span>
              <span className="truncate">Overall pressure</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className="h-full bg-tertiary" style={{ width: `${Math.min(m.congestionPct, 100)}%` }}></div>
            </div>
          </div>
          {/* Metric 3 */}
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant truncate">AT ANCHOR</span>
              <span className="material-symbols-outlined text-error text-[20px]">anchor</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`font-display-lg text-display-lg ${anchorSeverity.color}`}>{m.waiting}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">waiting</span>
            </div>
            <div className={`mt-2 flex items-center gap-1 ${anchorSeverity.color} font-body-sm text-body-sm`}>
              <span className="material-symbols-outlined text-[14px]">{anchorSeverity.icon}</span>
              <span className="truncate">{anchorSeverity.label}</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className={`h-full ${anchorSeverity.bar}`} style={{ width: `${Math.min(m.waiting * 10, 100)}%` }}></div>
            </div>
          </div>
          {/* Metric 4 */}
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant truncate">MAX WAVE</span>
              <span className="material-symbols-outlined text-secondary text-[20px]">water</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display-lg text-display-lg text-on-surface">{m.maxWave.toFixed(1)}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">meters</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-on-surface-variant font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[14px]">waves</span>
              <span className="truncate">Conditions</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className="h-full bg-secondary" style={{ width: `${wavePct}%` }}></div>
            </div>
          </div>
        </div>

        {aisDiagnostics && (
          <div className="lg:col-span-12 bg-surface-container-low border border-outline-variant/50 rounded-xl p-4 shadow-sm">
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`material-symbols-outlined text-[20px] ${providerCoverageIssue ? 'text-error' : 'text-secondary'}`}>
                    {providerCoverageIssue ? 'cell_tower' : 'radar'}
                  </span>
                  <h2 className="font-title-sm text-title-sm text-on-surface">AIS provider diagnostics</h2>
                  <span className="font-data-mono text-[10px] uppercase bg-surface-variant text-on-surface-variant px-2 py-0.5 rounded">
                    {aisDiagnostics.status.replaceAll('_', ' ')}
                  </span>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  {aisDiagnostics.detail ?? aisDiagnostics.message}
                </p>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-data-mono text-data-mono">
                <div>
                  <div className="text-on-surface-variant text-[10px] uppercase">50nm count</div>
                  <div className="text-on-surface">{aisDiagnostics.messageCountWithin50nm ?? 0}</div>
                </div>
                <div>
                  <div className="text-on-surface-variant text-[10px] uppercase">200nm count</div>
                  <div className="text-on-surface">{aisDiagnostics.messageCountWithin200nm ?? 0}</div>
                </div>
                <div>
                  <div className="text-on-surface-variant text-[10px] uppercase">Latest 50nm</div>
                  <div className="text-on-surface truncate">{formatDiagnosticValue(aisDiagnostics.latestMessageWithin50nm)}</div>
                </div>
                <div>
                  <div className="text-on-surface-variant text-[10px] uppercase">Latest 200nm</div>
                  <div className="text-on-surface truncate">{formatDiagnosticValue(aisDiagnostics.latestMessageWithin200nm)}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl overflow-hidden flex flex-col h-[600px] relative shadow-sm">
            <div className="p-4 border-b border-outline-variant/30 flex justify-between items-center bg-surface-container/90 backdrop-blur-sm z-10">
              <h2 className="font-title-sm text-title-sm text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">map</span>
                {port.name} Overview
              </h2>
            </div>
            <div ref={mapContainer} className="flex-1 w-full h-full bg-[#1b1c1b]">
               {/* MapLibre Container */}
            </div>
          </div>
        </div>

        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl flex flex-col shadow-sm">
            <div className="p-4 border-b border-outline-variant/30 bg-surface-container-low rounded-t-xl flex justify-between items-center">
              <h2 className="font-title-sm text-title-sm text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">format_list_bulleted</span>
                Active Traffic
              </h2>
              <span className="bg-primary-container text-on-primary-container px-2 py-0.5 rounded font-data-mono text-[10px] border border-primary/30">
                {providerCoverageIssue ? 'PROVIDER LIMITED' : `${port.vesselsTotal ?? port.vessels.length} TRACKED`}
              </span>
            </div>

            <div className="p-4 space-y-3">
              {previewVessels.length === 0 && (
                <div className="text-center py-10 text-on-surface-variant font-body-sm text-body-sm flex flex-col items-center gap-2">
                  <span className="material-symbols-outlined text-[28px] opacity-50">
                    {providerCoverageIssue ? 'cell_tower' : 'sailing'}
                  </span>
                  {providerCoverageIssue ? 'No AIS messages received from provider.' : 'No vessels surfaced in range right now.'}
                  {providerCoverageIssue && (
                    <span className="max-w-xs text-[11px] leading-4">
                      UAE/Gulf ports require second-source validation before live tracking claims.
                    </span>
                  )}
                </div>
              )}
              {previewVessels.map((vessel, idx) => (
                <div key={idx} className="bg-surface rounded-lg p-3 border border-outline-variant/50 flex flex-col gap-2">
                  <div className="flex justify-between items-baseline">
                    <span className="font-data-mono text-data-mono text-on-surface truncate font-bold">{vessel.name}</span>
                    <span className="font-data-mono text-[10px] bg-surface-variant px-1.5 py-0.5 rounded text-on-surface-variant uppercase">{vessel.zone}</span>
                  </div>
                  <div className="flex justify-between items-center font-body-sm text-body-sm text-on-surface-variant">
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">speed</span> {vessel.sog} kts</span>
                    <span
                      className="flex items-center gap-1"
                      title="Estimated ETA — heuristic from distance ÷ speed, not a model prediction"
                    >
                      <span className="material-symbols-outlined text-[14px]">schedule</span>
                      {vessel.eta || '--:--'}
                      <span className="text-[10px] opacity-60 ml-0.5">est.</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <Link
              to="/map"
              className="mt-auto p-3 border-t border-outline-variant/30 bg-surface-container-low rounded-b-xl text-center font-label-caps text-label-caps text-primary hover:bg-surface-variant transition-colors flex items-center justify-center gap-1"
            >
              {hiddenCount > 0
                ? `View ${port.vessels.length} surfaced of ${port.vesselsTotal ?? port.vessels.length} tracked in Traffic`
                : 'Open Traffic map'}
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
