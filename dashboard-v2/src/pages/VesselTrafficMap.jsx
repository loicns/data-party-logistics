import { useEffect, useRef, useState } from 'react';
import { useData } from '../context/DataContext';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

export default function VesselTrafficMap() {
  const { port } = useData();
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markersRef = useRef([]);
  const [selectedVessel, setSelectedVessel] = useState(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [activeZone, setActiveZone] = useState('all');

  useEffect(() => {
    if (map.current || !port) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/dark",
      center: [port.lon, port.lat],
      zoom: 11,
      attributionControl: false
    });

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
        setMapLoaded(false);
      }
    };
  }, [port]);

  useEffect(() => {
    if (!mapLoaded || !map.current || !port) return;

    // Clear existing markers
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    port.vessels.forEach((vessel) => {
      if (activeZone !== 'all' && vessel.zone !== activeZone) return;

      const el = document.createElement('div');
      el.className = 'w-4 h-4 rounded-full border-2 border-background shadow-sm cursor-pointer';

      if (vessel.zone === 'berth') el.style.backgroundColor = '#2dd96f';
      else if (vessel.zone === 'anchor') el.style.backgroundColor = '#f7b23b';
      else if (vessel.zone === 'approaching') el.style.backgroundColor = '#1ea7ff';
      else el.style.backgroundColor = '#7f8ea6';

      el.addEventListener('click', () => {
        setSelectedVessel(vessel);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([vessel.lon, vessel.lat])
        .addTo(map.current);

      markersRef.current.push(marker);
    });
  }, [port, mapLoaded, activeZone]);

  const handleRangeClick = (nm) => {
    if (!map.current || !port) return;
    // Rough conversion: zoom 8 is ~200nm, zoom 10 is ~50nm, zoom 12 is ~10nm
    let zoomLevel = 8;
    if (nm === 50) zoomLevel = 10;
    if (nm === 10) zoomLevel = 12;

    map.current.flyTo({
      center: [port.lon, port.lat],
      zoom: zoomLevel,
      essential: true
    });
  };

  if (!port) return null;

  return (
    <div className="flex-1 relative bg-[#111412] h-full overflow-hidden flex rounded-xl border border-outline-variant/30">

      {/* Filters & Controls */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex gap-4">
        {/* Range Controls */}
        <div className="bg-surface-container/90 backdrop-blur-sm border border-outline-variant rounded p-1 flex items-center shadow-[0px_4px_12px_rgba(0,0,0,0.5)]">
          {[200, 50, 10].map(range => (
            <button
              key={range}
              onClick={() => handleRangeClick(range)}
              className="px-3 py-1 text-label-sm font-label-caps rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors"
            >
              {range} NM
            </button>
          ))}
        </div>

        {/* Zone Filters */}
        <div className="bg-surface-container/90 backdrop-blur-sm border border-outline-variant rounded p-1 flex items-center shadow-[0px_4px_12px_rgba(0,0,0,0.5)]">
          {['all', 'berth', 'anchor', 'approaching', 'transit'].map(zone => (
            <button
              key={zone}
              onClick={() => setActiveZone(zone)}
              className={`px-3 py-1 text-label-sm font-label-caps rounded capitalize transition-colors ${
                activeZone === zone
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant'
              }`}
            >
              {zone}
            </button>
          ))}
        </div>
      </div>

      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2">
        <div className="bg-surface-container rounded border border-outline-variant flex flex-col shadow-[0px_4px_12px_rgba(0,0,0,0.5)]">
          <button className="p-2 text-on-surface hover:text-primary border-b border-outline-variant transition-colors" onClick={() => map.current?.zoomIn()}>
            <span className="material-symbols-outlined text-[20px]">add</span>
          </button>
          <button className="p-2 text-on-surface hover:text-primary transition-colors" onClick={() => map.current?.zoomOut()}>
            <span className="material-symbols-outlined text-[20px]">remove</span>
          </button>
        </div>
      </div>

      <div className="absolute bottom-4 left-4 z-20 bg-surface-container/90 backdrop-blur-sm border border-outline-variant rounded p-3 shadow-[0px_4px_12px_rgba(0,0,0,0.5)] font-body-sm text-body-sm">
        <div className="font-label-caps text-label-caps text-on-surface-variant mb-2">VESSEL STATUS</div>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#1ea7ff]"></div>
            <span className="text-on-surface">Approaching</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#f7b23b]"></div>
            <span className="text-on-surface">Drifting / Anchored</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#2dd96f]"></div>
            <span className="text-on-surface">Berthed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#7f8ea6]"></div>
            <span className="text-on-surface">Transit</span>
          </div>
        </div>
      </div>

      <div ref={mapContainer} className="absolute inset-0 z-10 w-full h-full bg-[#1b1c1b]"></div>

      {selectedVessel && (
        <aside className="absolute right-0 top-0 h-full w-80 bg-surface-container/95 backdrop-blur-md border-l border-outline-variant shadow-[-8px_0_24px_rgba(0,0,0,0.5)] z-30 flex flex-col transform transition-transform duration-300">
          <div className="p-6 border-b border-outline-variant flex justify-between items-start bg-surface-container-high">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="bg-[#1ea7ff]/20 text-[#94ccff] px-2 py-0.5 rounded-sm font-label-caps text-label-caps border border-[#1ea7ff]/50 uppercase">{selectedVessel.zone}</span>
                <span className="text-data-mono font-data-mono text-on-surface-variant text-[11px]">MMSI: {selectedVessel.mmsi}</span>
              </div>
              <h2 className="font-title-sm text-title-sm text-on-surface font-bold">{selectedVessel.name}</h2>
            </div>
            <button className="text-on-surface-variant hover:text-on-surface" onClick={() => setSelectedVessel(null)}>
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-surface border border-outline-variant rounded p-3">
                <div className="font-label-caps text-label-caps text-on-surface-variant mb-1">SPEED</div>
                <div className="font-data-mono text-data-mono text-on-surface text-lg">{selectedVessel.sog} <span className="text-body-sm text-on-surface-variant">kts</span></div>
              </div>
              <div className="bg-surface border border-outline-variant rounded p-3">
                <div className="font-label-caps text-label-caps text-on-surface-variant mb-1">DISTANCE</div>
                <div className="font-data-mono text-data-mono text-on-surface text-lg">{selectedVessel.dist} <span className="text-body-sm text-on-surface-variant">nm</span></div>
              </div>
              <div className="bg-surface border border-outline-variant rounded p-3 col-span-2 flex items-center justify-between">
                <div>
                  <div className="font-label-caps text-label-caps text-on-surface-variant mb-1">CONFIDENCE</div>
                  <div className="font-data-mono text-data-mono text-on-surface text-lg">{selectedVessel.conf}%</div>
                </div>
                <div className="text-right">
                  <div className="font-label-caps text-label-caps text-on-surface-variant mb-1">ETA</div>
                  <div className="font-data-mono text-data-mono text-primary text-lg">{selectedVessel.eta || '--:--'}</div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-4 flex flex-col gap-2">
              <button className="w-full bg-primary text-on-primary hover:bg-primary-fixed transition-colors py-2 rounded font-label-caps text-label-caps text-center">
                HAIL VESSEL (VHF 16)
              </button>
              <button className="w-full bg-transparent border border-outline-variant text-on-surface hover:bg-surface-variant transition-colors py-2 rounded font-label-caps text-label-caps text-center">
                ASSIGN PILOT
              </button>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
