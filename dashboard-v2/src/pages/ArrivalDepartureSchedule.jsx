import { useMemo, useState } from 'react';
import { useData } from '../context/DataContext';

const ZONE_META = {
  berth: { label: 'Berthed', tone: 'text-[#2dd96f]', badge: 'bg-[#2dd96f]/15 text-[#2dd96f] border-[#2dd96f]/25' },
  anchor: { label: 'At Anchor', tone: 'text-[#f7b23b]', badge: 'bg-[#f7b23b]/15 text-[#f7b23b] border-[#f7b23b]/25' },
  approaching: { label: 'Approaching', tone: 'text-[#1ea7ff]', badge: 'bg-[#1ea7ff]/15 text-[#1ea7ff] border-[#1ea7ff]/25' },
  transit: { label: 'In Transit', tone: 'text-[#7f8ea6]', badge: 'bg-[#7f8ea6]/15 text-[#d7dde6] border-[#7f8ea6]/25' },
};

function toNumber(value, fallback = 0) {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

function vesselStatus(vessel) {
  if (vessel.zone === 'berth') return 'Berthed';
  if (vessel.zone === 'anchor') return 'Waiting';
  if (vessel.zone === 'approaching') return 'Approaching';
  return 'In Transit';
}

function matchesMovement(vessel, movementFilter) {
  if (movementFilter === 'all') return true;
  if (movementFilter === 'inbound') return vessel.zone === 'approaching' || vessel.zone === 'transit';
  if (movementFilter === 'waiting') return vessel.zone === 'anchor';
  if (movementFilter === 'berthed') return vessel.zone === 'berth';
  return true;
}

// Numeric ETA proxy in hours — the same distance÷speed heuristic the export
// uses to render the ETA text. A string sort on "HH:MM"-ish text mis-orders
// mixed formats; vessels that aren't making way sort last.
function etaHours(vessel) {
  const sog = toNumber(vessel.sog);
  if (sog < 0.5) return Number.POSITIVE_INFINITY;
  return toNumber(vessel.dist) / sog;
}

function compareRows(left, right, sortBy) {
  if (sortBy === 'distance') return toNumber(left.dist) - toNumber(right.dist);
  if (sortBy === 'eta') return etaHours(left) - etaHours(right);
  if (sortBy === 'speed') return toNumber(right.sog) - toNumber(left.sog);
  return left.name.localeCompare(right.name);
}

export default function ArrivalDepartureSchedule() {
  const { port } = useData();
  const vessels = port?.vessels || [];
  const [search, setSearch] = useState('');
  const [zoneFilter, setZoneFilter] = useState('all');
  const [movementFilter, setMovementFilter] = useState('all');
  const [sortBy, setSortBy] = useState('distance');

  const zoneCounts = useMemo(
    () => vessels.reduce((acc, vessel) => {
      acc[vessel.zone] = (acc[vessel.zone] || 0) + 1;
      return acc;
    }, {}),
    [vessels]
  );

  const filteredVessels = useMemo(() => {
    const searchValue = search.trim().toLowerCase();
    return [...vessels]
      .filter((vessel) => zoneFilter === 'all' || vessel.zone === zoneFilter)
      .filter((vessel) => matchesMovement(vessel, movementFilter))
      .filter((vessel) => {
        if (!searchValue) return true;
        return vessel.name.toLowerCase().includes(searchValue) || vessel.mmsi.includes(searchValue);
      })
      .sort((left, right) => compareRows(left, right, sortBy));
  }, [movementFilter, search, sortBy, vessels, zoneFilter]);

  return (
    <div className="flex flex-col gap-gutter h-full">
      <div className="flex flex-col gap-4 mb-2">
        <div>
          <h2 className="font-headline-md text-headline-md text-on-surface mb-1">Port Traffic Board</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">Filter every vessel currently surfaced around {port?.name}, including waiting, berthed, and inbound traffic.</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-3">
            <div className="font-label-caps text-label-caps text-on-surface-variant">All Surfaced</div>
            <div className="font-display-md text-display-md text-on-surface mt-1">{vessels.length}</div>
          </div>
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-3">
            <div className="font-label-caps text-label-caps text-on-surface-variant">At Anchor</div>
            <div className="font-display-md text-display-md text-[#f7b23b] mt-1">{zoneCounts.anchor || 0}</div>
          </div>
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-3">
            <div className="font-label-caps text-label-caps text-on-surface-variant">Inbound</div>
            <div className="font-display-md text-display-md text-primary mt-1">{(zoneCounts.approaching || 0) + (zoneCounts.transit || 0)}</div>
          </div>
          <div className="bg-surface-container border border-outline-variant/50 rounded-xl p-3">
            <div className="font-label-caps text-label-caps text-on-surface-variant">Berthed</div>
            <div className="font-display-md text-display-md text-[#2dd96f] mt-1">{zoneCounts.berth || 0}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          <label className="flex items-center gap-2 border border-outline-variant bg-surface-container rounded-lg px-3 py-2">
            <span className="material-symbols-outlined text-[16px] text-on-surface-variant">search</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search vessel or MMSI"
              className="bg-transparent w-full outline-none text-on-surface font-body-sm text-body-sm placeholder:text-on-surface-variant"
            />
          </label>

          <select
            value={zoneFilter}
            onChange={(event) => setZoneFilter(event.target.value)}
            className="border border-outline-variant bg-surface-container text-on-surface rounded-lg px-3 py-2 font-body-sm text-body-sm outline-none focus:border-primary"
          >
            <option value="all">All zones</option>
            {Object.entries(ZONE_META).map(([zone, meta]) => (
              <option key={zone} value={zone}>{meta.label}</option>
            ))}
          </select>

          <select
            value={movementFilter}
            onChange={(event) => setMovementFilter(event.target.value)}
            className="border border-outline-variant bg-surface-container text-on-surface rounded-lg px-3 py-2 font-body-sm text-body-sm outline-none focus:border-primary"
          >
            <option value="all">All movement states</option>
            <option value="inbound">Inbound only</option>
            <option value="waiting">Waiting only</option>
            <option value="berthed">Berthed only</option>
          </select>

          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
            className="border border-outline-variant bg-surface-container text-on-surface rounded-lg px-3 py-2 font-body-sm text-body-sm outline-none focus:border-primary"
          >
            <option value="distance">Sort by distance</option>
            <option value="eta">Sort by ETA (est.)</option>
            <option value="speed">Sort by speed</option>
            <option value="name">Sort by vessel name</option>
          </select>
        </div>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant/50 overflow-hidden flex flex-col shadow-lg shadow-black/20 flex-1">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-high border-b border-outline-variant/50 sticky top-0 z-10">
              <tr>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold w-1/4">Vessel Name</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold">MMSI</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold">Zone</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold">Distance</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold">Speed</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold" title="Estimated from distance ÷ speed — not a model prediction">ETA (est.)</th>
                <th className="font-label-caps text-label-caps text-on-surface-variant py-3 px-4 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 bg-surface-container font-body-md text-body-md">
              {filteredVessels.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-on-surface-variant font-body-md">
                    No vessels match the current filters.
                  </td>
                </tr>
              ) : (
                filteredVessels.map((item, idx) => {
                  const zoneMeta = ZONE_META[item.zone] || ZONE_META.transit;
                  return (
                    <tr key={`${item.mmsi}-${idx}`} className="hover:bg-surface-container-highest transition-colors group">
                      <td className="py-data-density-padding px-4 flex items-center gap-3">
                        <span className={`material-symbols-outlined text-[20px] opacity-70 group-hover:opacity-100 transition-opacity ${zoneMeta.tone}`}>directions_boat</span>
                        <span className="text-on-surface font-medium">{item.name}</span>
                      </td>
                      <td className="py-data-density-padding px-4 font-data-mono text-data-mono text-on-surface-variant">{item.mmsi}</td>
                      <td className="py-data-density-padding px-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded border font-label-caps text-label-caps tracking-widest uppercase ${zoneMeta.badge}`}>
                          {zoneMeta.label}
                        </span>
                      </td>
                      <td className="py-data-density-padding px-4 text-on-surface">{toNumber(item.dist).toFixed(1)} NM</td>
                      <td className="py-data-density-padding px-4 font-data-mono text-data-mono text-on-surface-variant">{toNumber(item.sog).toFixed(1)} kn</td>
                      <td className="py-data-density-padding px-4 font-data-mono text-data-mono text-on-surface">{item.eta}</td>
                      <td className="py-data-density-padding px-4 text-right">
                        <span className="inline-flex items-center px-2 py-1 rounded bg-secondary-container text-on-secondary-container font-label-caps text-label-caps tracking-widest border border-secondary/20 uppercase">
                          {vesselStatus(item)}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-outline-variant/50 bg-surface-container-low p-3 flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm mt-auto">
          <div>Showing {filteredVessels.length} of {vessels.length} vessels around {port?.name}</div>
        </div>
      </div>
    </div>
  );
}
