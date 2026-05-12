import { useData } from '../context/DataContext';

export default function SourceHealthPills() {
  const { sources } = useData();

  if (!sources || sources.length === 0) return null;

  const getIcon = (name) => {
    if (name.includes('AIS')) return 'satellite_alt';
    if (name.includes('Weather')) return 'water';
    return 'database';
  };

  return (
    <div className="hidden lg:flex items-center gap-2 border-r border-outline-variant/30 pr-4 mr-2">
      {sources.map((source, idx) => (
        <div
          key={idx}
          className="group relative flex items-center justify-center bg-surface-container-high rounded-full w-8 h-8 border border-outline-variant/50 hover:bg-surface-variant transition-colors cursor-help"
        >
          <div className="absolute top-0 right-0 flex h-2 w-2 -mt-0.5 -mr-0.5">
            {source.status === 'active' && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            )}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${source.status === 'active' ? 'bg-primary' : 'bg-error'}`}></span>
          </div>
          <span className="material-symbols-outlined text-[16px] text-on-surface-variant group-hover:text-primary transition-colors">{getIcon(source.name)}</span>

          {/* Tooltip on Hover */}
          <div className="absolute top-full mt-2 right-0 hidden group-hover:block z-50 w-48 bg-surface-container-highest border border-outline-variant/50 rounded-lg shadow-lg p-3 pointer-events-none">
            <div className="font-label-md text-label-md text-on-surface font-bold mb-1">{source.name}</div>
            <div className="font-body-sm text-body-sm text-on-surface-variant mb-2">{source.detail}</div>
            <div className="flex items-center gap-2 text-[10px] font-label-caps uppercase text-on-surface-variant">
              <span className={`w-1.5 h-1.5 rounded-full ${source.status === 'active' ? 'bg-primary' : 'bg-error'}`}></span>
              Last updated: {source.freshness}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
