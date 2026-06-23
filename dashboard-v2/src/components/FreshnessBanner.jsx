import { useState, useEffect } from 'react';
import { useData } from '../context/DataContext';

// Parse the export timestamp. Accepts "2026-06-11 09:04 UTC" or ISO strings.
function parseGeneratedAt(value) {
  if (!value) return null;
  const iso = value.includes('UTC')
    ? value.replace(' UTC', 'Z').replace(' ', 'T')
    : value;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

function ageLabel(hours) {
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 24) return `${Math.round(hours)} h`;
  return `${Math.round(hours / 24)} d`;
}

function sourceAgeHours(freshness) {
  if (!freshness) return null;
  const match = freshness.match(/^(\d+)\s*(min|h|d)\s+ago$/i);
  if (!match) return null;
  const value = Number(match[1]);
  if (!Number.isFinite(value)) return null;
  if (match[2].toLowerCase() === 'min') return value / 60;
  if (match[2].toLowerCase() === 'h') return value;
  return value * 24;
}

// NFR1: the dashboard forecast should be <= 2 h old. When it isn't, a viewer
// must SEE that the pipeline is stale instead of mistaking zeros for a calm
// port. Silent during fresh windows; amber 2-12 h; red beyond.
export default function FreshnessBanner() {
  const { metadata, sources } = useData();
  // Re-evaluate age every minute so the banner appears as data goes stale.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const aisSource = sources.find((source) => source.name.includes('AIS'));
  const aisAgeHours = sourceAgeHours(aisSource?.freshness);
  if (aisSource?.status && aisSource.status !== 'active') {
    const severe = aisAgeHours === null || aisAgeHours > 12;
    const tone = severe
      ? 'bg-error/15 border-error/40 text-error'
      : 'bg-[#f7b23b]/15 border-[#f7b23b]/40 text-[#f7b23b]';

    return (
      <div
        role="status"
        className={`flex items-center gap-3 px-4 py-2 border-b font-body-sm text-body-sm ${tone}`}
      >
        <span className="material-symbols-outlined text-[18px]">
          {severe ? 'error' : 'warning'}
        </span>
        <span>
          <strong>AIS vessel positions are stale.</strong>{' '}
          <span className="text-on-surface-variant">
            Last AIS update was {aisSource.freshness}; vessel counts may show
            zero until ingestion catches up.
          </span>
        </span>
      </div>
    );
  }

  const generated = parseGeneratedAt(metadata?.generatedAt);
  if (!generated) return null;

  const ageHours = (now - generated.getTime()) / 3.6e6;
  if (ageHours <= 2) return null; // within SLA — no banner

  const severe = ageHours > 12;
  const tone = severe
    ? 'bg-error/15 border-error/40 text-error'
    : 'bg-[#f7b23b]/15 border-[#f7b23b]/40 text-[#f7b23b]';

  return (
    <div
      role="status"
      className={`flex items-center gap-3 px-4 py-2 border-b font-body-sm text-body-sm ${tone}`}
    >
      <span className="material-symbols-outlined text-[18px]">
        {severe ? 'error' : 'warning'}
      </span>
      <span>
        <strong>Data is {ageLabel(ageHours)} old.</strong>{' '}
        <span className="text-on-surface-variant">
          The ingestion pipeline may be delayed — showing the last successful
          snapshot from {metadata.generatedAt}. Metrics below reflect that
          snapshot, not the current moment.
        </span>
      </span>
    </div>
  );
}
