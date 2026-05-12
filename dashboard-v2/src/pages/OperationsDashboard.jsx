import { useEffect, useRef } from 'react';
import { useData } from '../context/DataContext';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

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
              <span className="font-display-lg text-display-lg text-on-surface">{m.tracked}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">active</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-secondary font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
              <span>Live updates</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className="h-full bg-primary w-[100%]"></div>
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
              <div className="h-full bg-tertiary w-[30%]"></div>
            </div>
          </div>
          {/* Metric 3 */}
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant truncate">AT ANCHOR</span>
              <span className="material-symbols-outlined text-error text-[20px]">anchor</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display-lg text-display-lg text-on-surface text-error">{m.waiting}</span>
              <span className="font-body-md text-body-md text-on-surface-variant">waiting</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-error font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[14px]">warning</span>
              <span className="truncate">High congestion</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-surface-variant">
              <div className="h-full bg-error" style={{ width: `${Math.min(m.waiting * 10, 100)}%` }}></div>
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
              <div className="h-full bg-secondary w-[40%]"></div>
            </div>
          </div>
        </div>

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
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl flex flex-col flex-1 h-[600px] shadow-sm">
            <div className="p-4 border-b border-outline-variant/30 bg-surface-container-low rounded-t-xl flex justify-between items-center">
              <h2 className="font-title-sm text-title-sm text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">format_list_bulleted</span>
                Active Traffic
              </h2>
              <span className="bg-primary-container text-on-primary-container px-2 py-0.5 rounded font-data-mono text-[10px] border border-primary/30">{port.vessels.length} TOTAL</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {port.vessels.map((vessel, idx) => (
                <div key={idx} className="bg-surface rounded-lg p-3 border border-outline-variant/50 hover:border-primary/50 transition-colors cursor-pointer group flex flex-col gap-2">
                  <div className="flex justify-between items-baseline">
                    <span className="font-data-mono text-data-mono text-on-surface truncate font-bold">{vessel.name}</span>
                    <span className="font-data-mono text-[10px] bg-surface-variant px-1.5 py-0.5 rounded text-on-surface-variant uppercase">{vessel.zone}</span>
                  </div>
                  <div className="flex justify-between items-center font-body-sm text-body-sm text-on-surface-variant">
                    <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">speed</span> {vessel.sog} kts</span>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-1" title={`ETA Confidence: ${vessel.conf}%`}>
                        <span className="font-data-mono text-[10px] opacity-70">{vessel.conf}%</span>
                        <div className="w-8 h-1 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className={`h-full ${vessel.conf >= 90 ? 'bg-primary' : vessel.conf >= 70 ? 'bg-tertiary' : 'bg-error'}`} style={{ width: `${vessel.conf}%` }}></div>
                        </div>
                      </div>
                      <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">schedule</span> {vessel.eta}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-outline-variant/30 bg-surface-container-low rounded-b-xl text-center font-body-sm text-body-sm text-on-surface-variant">
              Showing all {port.vessels.length} surfaced vessels for this port
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
