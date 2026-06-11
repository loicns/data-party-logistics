import { useData } from '../context/DataContext';

export default function BerthSchedulingView() {
  const { port } = useData();
  const berths = port?.berthAllocations || [];
  const berthed = port?.metrics?.berthed ?? 0;

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden relative">
      <div className="h-16 border-b border-outline-variant bg-surface-container flex items-center justify-between px-container-padding flex-shrink-0">
        <div className="flex flex-col">
          <h2 className="font-title-sm text-title-sm">Berth Occupancy (AIS-derived)</h2>
          {berths.length > 0 && (
            <span className="text-xs text-on-surface-variant">
              {berthed} of {berths.length} berths occupied (aggregate) · which specific berth is occupied is not observable from AIS — card positions are illustrative
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-primary inline-block"></span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">Occupied</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-surface-variant inline-block border border-outline"></span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">Available</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-container-padding">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {berths.map((berth) => (
            <div
              key={berth.id}
              className={`p-4 rounded-xl border ${
                berth.status === 'occupied'
                  ? 'bg-primary-container/10 border-primary/30'
                  : 'bg-surface-container border-outline-variant'
              }`}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-title-md text-title-md text-on-surface">{berth.name}</h3>
                  <span className={`inline-flex items-center mt-1 px-2 py-0.5 rounded text-xs font-label-caps uppercase ${
                    berth.status === 'occupied' ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'
                  }`}>
                    {berth.status}
                  </span>
                </div>
                <span className="material-symbols-outlined text-on-surface-variant opacity-50">
                  {berth.status === 'occupied' ? 'directions_boat' : 'anchor'}
                </span>
              </div>

              {berth.status === 'occupied' ? (
                <div className="bg-surface p-3 rounded border border-outline-variant flex flex-col items-center justify-center h-[88px] text-center">
                  <div className="text-sm text-on-surface">Vessel in berth zone</div>
                  <div className="text-xs text-on-surface-variant mt-1">
                    identity not mapped to terminal
                  </div>
                </div>
              ) : (
                <div className="bg-surface/50 p-3 rounded border border-outline-variant border-dashed flex items-center justify-center h-[88px]">
                  <span className="text-on-surface-variant text-sm">No vessel detected</span>
                </div>
              )}
            </div>
          ))}
        </div>
        {berths.length === 0 && (
          <div className="flex items-center justify-center h-64 text-on-surface-variant">
            No berth data available for this port.
          </div>
        )}
      </div>
    </div>
  );
}
