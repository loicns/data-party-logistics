import { useState, useEffect, useRef, useCallback } from 'react';

const AIS_WS_URL = 'wss://stream.aisstream.io/v0/stream';
const STALE_THRESHOLD_MS = 5 * 60 * 1000; // Drop vessels not seen in 5 minutes
const CLEANUP_INTERVAL_MS = 60 * 1000;     // Run cleanup every 60 seconds

/**
 * Custom hook that connects the browser directly to the AISStream WebSocket
 * and maintains a live map of vessel positions around the selected port.
 *
 * Zero AWS cost — runs entirely in the browser.
 *
 * @param {string|null} apiKey  - AISStream API key (null = stay disconnected)
 * @param {object|null} port    - Current port object with { lat, lon, code }
 * @returns {{ liveVessels: Array, status: string, vesselCount: number }}
 */
export function useLiveAis(apiKey, port) {
  const [liveVessels, setLiveVessels] = useState([]);
  const [status, setStatus] = useState('disconnected'); // disconnected | connecting | connected | error
  const wsRef = useRef(null);
  const vesselsRef = useRef(new Map()); // MMSI → vessel object (mutable for perf)

  // Flush the Map into React state (called after each batch of updates)
  const flush = useCallback(() => {
    setLiveVessels(Array.from(vesselsRef.current.values()));
  }, []);

  // ── Main WebSocket lifecycle ──────────────────────────────────────────────
  useEffect(() => {
    if (!apiKey || !port?.lat || !port?.lon) {
      setStatus('disconnected');
      return;
    }

    // Build a ~50 nm bounding box around the port (~0.83 degrees)
    const delta = 0.83;
    const box = [[
      [port.lat - delta, port.lon - delta],
      [port.lat + delta, port.lon + delta],
    ]];

    setStatus('connecting');
    const ws = new WebSocket(AIS_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      ws.send(JSON.stringify({
        APIKey: apiKey,
        BoundingBoxes: box,
        FilterMessageTypes: ['PositionReport'],
      }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.MessageType !== 'PositionReport') return;

        const r = msg.Message?.PositionReport;
        const meta = msg.MetaData;
        if (!r || !meta) return;

        const mmsi = meta.MMSI;
        const shipName = (meta.ShipName || '').trim() || `MMSI ${mmsi}`;

        // Compute rough distance to port centre (degrees → nm, good enough for UI)
        const dLat = r.Latitude - port.lat;
        const dLon = (r.Longitude - port.lon) * Math.cos((port.lat * Math.PI) / 180);
        const distNm = Math.sqrt(dLat * dLat + dLon * dLon) * 60;

        // Simple zone classification
        let zone = 'transit';
        if (distNm <= 2 && r.Sog < 1) zone = 'berth';
        else if (distNm <= 5 && r.Sog < 1) zone = 'anchor';
        else if (distNm <= 30) zone = 'approaching';

        vesselsRef.current.set(mmsi, {
          mmsi,
          name: shipName,
          lat: r.Latitude,
          lon: r.Longitude,
          sog: r.Sog != null ? Number(r.Sog.toFixed(1)) : 0,
          cog: r.Cog != null ? Number(r.Cog.toFixed(0)) : 0,
          zone,
          dist: Number(distNm.toFixed(1)),
          conf: 100,
          eta: '--:--',
          lastSeen: Date.now(),
        });

        flush();
      } catch {
        // Silently ignore malformed messages
      }
    };

    ws.onerror = () => setStatus('error');

    ws.onclose = () => {
      // Only set disconnected if this is still the active socket
      if (wsRef.current === ws) {
        setStatus('disconnected');
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      vesselsRef.current.clear();
      setLiveVessels([]);
    };
  }, [apiKey, port?.code, port?.lat, port?.lon, flush]);

  // ── Stale vessel cleanup ──────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      const cutoff = Date.now() - STALE_THRESHOLD_MS;
      let changed = false;
      for (const [mmsi, v] of vesselsRef.current) {
        if (v.lastSeen < cutoff) {
          vesselsRef.current.delete(mmsi);
          changed = true;
        }
      }
      if (changed) flush();
    }, CLEANUP_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [flush]);

  return { liveVessels, status, vesselCount: liveVessels.length };
}
