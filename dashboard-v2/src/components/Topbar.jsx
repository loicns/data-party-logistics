import { useState } from 'react';
import { useData } from '../context/DataContext';
import SourceHealthPills from './SourceHealthPills';

export default function Topbar({ onMenuClick }) {
  const { ports, currentPortCode, setCurrentPortCode, port } = useData();
  const [searchQuery, setSearchQuery] = useState('');

  const searchResults = searchQuery.length > 1 && port ?
    port.vessels.filter(v => v.name.toLowerCase().includes(searchQuery.toLowerCase()) || (v.mmsi && v.mmsi.includes(searchQuery)))
    : [];

  return (
    <header className="bg-surface-container flex justify-between items-center h-16 w-full px-6 flex-shrink-0 border-b border-outline-variant/50 relative z-40">
      <div className="flex items-center gap-6">
        <div className="md:hidden">
          <button
            className="text-on-surface p-2 -ml-2 rounded-lg hover:bg-surface-variant"
            onClick={onMenuClick}
          >
            <span className="material-symbols-outlined">menu</span>
          </button>
        </div>
        <div className="font-headline-md text-headline-md font-black tracking-tight text-primary flex items-center gap-2 sm:gap-4 whitespace-nowrap">
          <span className="hidden sm:inline">MARITIME OPS</span>
          {/* Port Switcher */}
          <select
            value={currentPortCode}
            onChange={(e) => setCurrentPortCode(e.target.value)}
            className="ml-4 bg-surface-container-high border border-outline-variant/50 rounded-md px-3 py-1 text-body-md text-on-surface focus:ring-primary focus:border-primary outline-none"
          >
            {Object.entries(ports).map(([code, p]) => (
              <option key={code} value={code}>{p.name} ({code})</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-4 relative">
        <SourceHealthPills />
        <div className="relative">
          <div className="hidden md:flex items-center bg-surface-container-high rounded-full px-4 py-1.5 border border-outline-variant/50 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20 transition-all z-50">
            <span className="material-symbols-outlined text-on-surface-variant text-[20px] mr-2">search</span>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none outline-none text-body-md font-body-md text-on-surface placeholder:text-on-surface-variant/70 w-32 lg:w-48 xl:w-64 focus:ring-0 p-0 transition-all"
              placeholder="Search vessels, MMSI..."
              type="text"
            />
          </div>

          {searchQuery.length > 1 && (
            <div className="absolute top-12 left-0 w-[300px] bg-surface-container-high border border-outline-variant/50 rounded-lg shadow-xl overflow-hidden z-50 flex flex-col max-h-[400px]">
              <div className="p-3 border-b border-outline-variant/50 font-label-caps text-label-caps text-on-surface-variant bg-surface-container">
                {searchResults.length} RESULTS FOUND
              </div>
              <div className="overflow-y-auto">
                {searchResults.length > 0 ? searchResults.map((v, i) => (
                  <div key={i} className="p-3 border-b border-outline-variant/30 hover:bg-surface-variant cursor-pointer transition-colors flex justify-between items-center group">
                    <div>
                      <div className="font-bold text-on-surface text-body-sm group-hover:text-primary">{v.name}</div>
                      <div className="text-on-surface-variant font-data-mono text-[10px]">MMSI: {v.mmsi || 'UNKNOWN'}</div>
                    </div>
                    <span className="bg-surface-container-low text-on-surface px-1.5 py-0.5 rounded font-label-caps text-[10px] uppercase border border-outline-variant/50">{v.zone}</span>
                  </div>
                )) : (
                  <div className="p-4 text-center text-on-surface-variant text-body-sm">No vessels found matching "{searchQuery}"</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
