import { useState } from 'react';
import { useData } from '../context/DataContext';

const ZONE_META = {
  berth:      { color: '#2dd96f', label: 'Berthed' },
  anchor:     { color: '#f7b23b', label: 'At Anchor' },
  approaching:{ color: '#1ea7ff', label: 'Approaching' },
  transit:    { color: '#7f8ea6', label: 'In Transit' },
};

function congestionColor(score) {
  if (score >= 0.65) return '#ef4444';   // red
  if (score >= 0.35) return '#f7b23b';   // amber
  return '#2dd96f';                       // green
}

export default function CongestionInsights() {
  const { port, trendLabels, metadata } = useData();
  const [zoneFilter, setZoneFilter] = useState('all');

  if (!port) return null;

  const { metrics, vessels = [], berthAllocations = [], trend = [] } = port;

  // ── Zone breakdown derived from vessels array ───────────────────────────
  const zoneCounts = vessels.reduce((acc, v) => {
    acc[v.zone] = (acc[v.zone] || 0) + 1;
    return acc;
  }, {});

  const totalByZone = Object.values(zoneCounts).reduce((a, b) => a + b, 0) || 1;

  // ── Berth utilisation ───────────────────────────────────────────────────
  const occupiedCount = berthAllocations.filter(b => b.status === 'occupied').length;
  const berthTotal = berthAllocations.length || 1;
  const berthUtilPct = Math.round((occupiedCount / berthTotal) * 100);

  // ── Filtered vessel list for the table ─────────────────────────────────
  const filteredVessels = zoneFilter === 'all'
    ? vessels
    : vessels.filter(v => v.zone === zoneFilter);

  // ── Trend chart max ─────────────────────────────────────────────────────
  const maxTrend = Math.max(...trend, 0.01);

  return (
    <div className="flex flex-col gap-6 flex-1">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-3">
        <div>
          <h2 className="font-display-lg text-display-lg text-on-surface mb-1">Congestion Analytics</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            {port.name} — {metadata?.generatedAt ? `Snapshot: ${metadata.generatedAt}` : 'Live snapshot'}
          </p>
        </div>
        <select
          value={zoneFilter}
          onChange={e => setZoneFilter(e.target.value)}
          className="bg-surface-container border border-outline-variant text-on-surface font-body-sm text-body-sm rounded px-3 py-2 outline-none focus:border-primary"
        >
          <option value="all">All Zones</option>
          {Object.keys(ZONE_META).map(z => (
            <option key={z} value={z}>{ZONE_META[z].label}</option>
          ))}
        </select>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Tracked', value: metrics.tracked, unit: 'vessels', color: 'text-primary' },
          { label: 'At Anchor', value: metrics.waiting, unit: 'waiting', color: 'text-[#f7b23b]' },
          { label: 'Congestion Score', value: `${metrics.congestionPct}%`, unit: 'of capacity', color: metrics.congestionPct > 65 ? 'text-error' : metrics.congestionPct > 35 ? 'text-[#f7b23b]' : 'text-[#2dd96f]' },
          { label: 'Berth Utilisation', value: `${berthUtilPct}%`, unit: `${occupiedCount}/${berthAllocations.length} berths`, color: berthUtilPct > 80 ? 'text-error' : 'text-primary' },
        ].map(({ label, value, unit, color }) => (
          <div key={label} className="bg-surface-container border border-outline-variant/50 rounded-xl p-4 flex flex-col gap-1 shadow-sm">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wide">{label}</span>
            <span className={`text-3xl font-bold ${color}`}>{value}</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">{unit}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 6-day trend chart */}
        <div className="lg:col-span-7 bg-surface-container border border-outline-variant/50 rounded-xl p-6 shadow-sm flex flex-col">
          <h3 className="font-title-sm text-title-sm text-on-surface mb-5">6-Day Congestion Trend</h3>
          {trend.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body-sm">No trend data in export</div>
          ) : (
            <>
              <div className="flex items-end gap-2 flex-1 h-[140px]">
                {trend.map((score, i) => {
                  const pct = Math.round((score / maxTrend) * 100);
                  const col = congestionColor(score);
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1 group cursor-default" title={`${trendLabels[i]}: ${Math.round(score * 100)}%`}>
                      <span className="font-data-mono text-[10px] text-on-surface-variant">{Math.round(score * 100)}%</span>
                      <div
                        className="w-full rounded-t-sm transition-all"
                        style={{ height: `${Math.max(pct * 1.2, 4)}px`, backgroundColor: col, opacity: 0.8 }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-2">
                {trendLabels.map((label, i) => (
                  <span key={i} className="font-label-caps text-[9px] text-on-surface-variant flex-1 text-center">{label}</span>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Zone breakdown */}
        <div className="lg:col-span-5 bg-surface-container border border-outline-variant/50 rounded-xl p-6 shadow-sm">
          <h3 className="font-title-sm text-title-sm text-on-surface mb-5">Zone Distribution</h3>
          <div className="space-y-4">
            {Object.entries(ZONE_META).map(([zone, { color, label }]) => {
              const count = zoneCounts[zone] || 0;
              const pct = Math.round((count / totalByZone) * 100);
              return (
                <div key={zone}>
                  <div className="flex justify-between mb-1.5">
                    <span className="font-body-sm text-body-sm font-medium" style={{ color }}>{label}</span>
                    <span className="font-data-mono text-[11px] text-on-surface-variant">{count} — {pct}%</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Terminal status grid */}
        <div className="lg:col-span-12 bg-surface-container border border-outline-variant/50 rounded-xl p-6 shadow-sm">
          <h3 className="font-title-sm text-title-sm text-on-surface mb-5">Terminal Status</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {berthAllocations.map((b) => (
              <div
                key={b.id}
                className={`rounded-lg p-3 border flex flex-col gap-1.5 ${
                  b.status === 'occupied'
                    ? 'bg-[#2dd96f]/10 border-[#2dd96f]/40'
                    : 'bg-surface-variant/20 border-outline-variant/30'
                }`}
              >
                <span className="font-label-caps text-label-caps text-on-surface-variant truncate text-[10px]">{b.name}</span>
                <span className={`font-bold text-body-sm ${b.status === 'occupied' ? 'text-[#2dd96f]' : 'text-on-surface-variant'}`}>
                  {b.status === 'occupied' ? '● Occupied' : '○ Available'}
                </span>
                {b.vessel && (
                  <span className="font-data-mono text-[10px] text-on-surface-variant truncate" title={b.vessel}>
                    {b.vessel}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Filtered vessel table */}
        <div className="lg:col-span-12 bg-surface-container border border-outline-variant/50 rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-3 border-b border-outline-variant/50 bg-surface-container-high flex justify-between items-center">
            <h3 className="font-title-sm text-title-sm text-on-surface">
              Vessel List {zoneFilter !== 'all' ? `— ${ZONE_META[zoneFilter]?.label}` : ''}
            </h3>
            <span className="font-label-caps text-label-caps text-on-surface-variant">{filteredVessels.length} VESSELS</span>
          </div>
          <div className="overflow-x-auto max-h-[280px] overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-surface-container-high border-b border-outline-variant/50">
                <tr>
                  {['Vessel', 'MMSI', 'Zone', 'Distance', 'SOG', 'ETA', 'Conf'].map(h => (
                    <th key={h} className="font-label-caps text-label-caps text-on-surface-variant py-2 px-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {filteredVessels.length === 0 ? (
                  <tr><td colSpan={7} className="py-6 text-center text-on-surface-variant font-body-sm">No vessels in this zone.</td></tr>
                ) : filteredVessels.map((v, i) => {
                  const zm = ZONE_META[v.zone];
                  return (
                    <tr key={`${v.mmsi}-${i}`} className="hover:bg-surface-variant/30 transition-colors">
                      <td className="py-2 px-4 font-medium text-on-surface text-body-sm truncate max-w-[160px]">{v.name}</td>
                      <td className="py-2 px-4 font-data-mono text-[11px] text-on-surface-variant">{v.mmsi}</td>
                      <td className="py-2 px-4">
                        <span className="font-label-caps text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${zm?.color}20`, color: zm?.color }}>
                          {zm?.label ?? v.zone}
                        </span>
                      </td>
                      <td className="py-2 px-4 font-data-mono text-[11px] text-on-surface-variant">{v.dist} nm</td>
                      <td className="py-2 px-4 font-data-mono text-[11px] text-on-surface-variant">{v.sog} kn</td>
                      <td className="py-2 px-4 font-data-mono text-[11px] text-on-surface">{v.eta}</td>
                      <td className="py-2 px-4">
                        <div className="flex items-center gap-1.5">
                          <div className="w-10 h-1.5 bg-surface-variant rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${v.conf}%`, backgroundColor: v.conf >= 80 ? '#2dd96f' : v.conf >= 65 ? '#f7b23b' : '#ef4444' }} />
                          </div>
                          <span className="font-data-mono text-[10px] text-on-surface-variant">{v.conf}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
