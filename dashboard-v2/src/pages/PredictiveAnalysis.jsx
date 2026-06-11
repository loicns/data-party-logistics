import { useData } from '../context/DataContext';
import { usePredictions } from '../hooks/usePredictions';

const RISK_COLOR = { Nominal: '#2dd96f', Elevated: '#f7b23b', High: '#ef4444' };

function deriveRisk(congestionPct) {
  if (congestionPct >= 65) return 'High';
  if (congestionPct >= 35) return 'Elevated';
  return 'Nominal';
}

export default function PredictiveAnalysis() {
  const { port, outlookLabels, metadata, currentPortCode } = useData();
  const predictions = usePredictions();

  if (!port) return null;

  // The ML model's actual 24h-ahead output (predictions.json from the cloud
  // loop) — the headline of this page, not a derived heuristic.
  const model = predictions?.[currentPortCode] ?? null;
  const modelPct = model ? Math.round(model.probability * 100) : null;
  const modelColor = model
    ? model.probability >= 0.65 ? '#ef4444' : model.probability >= 0.35 ? '#f7b23b' : '#2dd96f'
    : undefined;

  const { metrics, vessels = [], schedule = [], forecast = [] } = port;
  const risk = deriveRisk(metrics.congestionPct);

  // Distance buckets from vessels array
  const buckets = [
    { label: '0–10 nm',   vessels: vessels.filter(v => v.dist <= 10) },
    { label: '10–50 nm',  vessels: vessels.filter(v => v.dist > 10 && v.dist <= 50) },
    { label: '50–100 nm', vessels: vessels.filter(v => v.dist > 50 && v.dist <= 100) },
    { label: '100–150 nm',vessels: vessels.filter(v => v.dist > 100 && v.dist <= 150) },
    { label: '150–200 nm',vessels: vessels.filter(v => v.dist > 150) },
  ];
  const maxBucket = Math.max(...buckets.map(b => b.vessels.length), 1);

  // Forecast bars (0.0-1.0 scores, labelled by outlookLabels)
  const maxForecast = Math.max(...forecast, 0.01);

  return (
    <div className="flex flex-col gap-6 w-full">
      <div>
        <h3 className="font-display-lg text-display-lg text-on-surface mb-1">Predictive Overview</h3>
        <p className="font-body-md text-body-md text-on-surface-variant">
          {port.name} — {metadata?.generatedAt ? `Snapshot: ${metadata.generatedAt}` : 'Heuristic forecasts'}
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex flex-col gap-2 rounded-xl p-6 bg-surface-container border border-primary/40 shadow-sm">
          <p className="text-on-surface-variant font-body-md font-medium">Model 24h Forecast</p>
          {model ? (
            <>
              <p className="tracking-tight text-3xl font-bold" style={{ color: modelColor }}>
                {modelPct}% <span className="text-body-md font-medium text-on-surface-variant">{model.prediction ? 'Congested' : 'Clear'}</span>
              </p>
              <p className="font-body-sm text-on-surface-variant">
                LightGBM P(congested in 24h) · features as of {model.as_of}
              </p>
            </>
          ) : (
            <>
              <p className="tracking-tight text-3xl font-bold text-on-surface-variant">—</p>
              <p className="font-body-sm text-on-surface-variant">model output unavailable for this port</p>
            </>
          )}
        </div>
        <div className="flex flex-col gap-2 rounded-xl p-6 bg-surface-container border border-outline-variant shadow-sm">
          <p className="text-on-surface-variant font-body-md font-medium">Incoming Queue</p>
          <p className="text-primary tracking-tight text-3xl font-bold">{schedule.length}</p>
          <p className="font-body-sm text-on-surface-variant">vessels approaching / in transit</p>
        </div>
        <div className={`flex flex-col gap-2 rounded-xl p-6 bg-surface-container border shadow-sm ${risk === 'High' ? 'border-error/50' : 'border-outline-variant'}`}>
          <p className="text-on-surface-variant font-body-md font-medium">Overall Risk</p>
          <p className="tracking-tight text-3xl font-bold" style={{ color: RISK_COLOR[risk] }}>{risk}</p>
          <p className="font-body-sm text-on-surface-variant">{metrics.waiting} vessel{metrics.waiting !== 1 ? 's' : ''} at anchor</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Forecast bar chart from real export data */}
        <section className="bg-surface-container rounded-xl border border-outline-variant p-6 flex flex-col gap-4 shadow-sm">
          <div>
            <h3 className="text-title-lg text-on-surface font-bold">Congestion Trend — last 5 days</h3>
            <p className="font-body-sm text-on-surface-variant">Observed history from the feature tables. The forward-looking number is the Model 24h Forecast above.</p>
          </div>
          {forecast.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body-sm">No trend data in export</div>
          ) : (
            <>
              <div className="flex items-end gap-3 h-[140px] mt-2">
                {forecast.map((score, i) => {
                  const pct = Math.round((score / maxForecast) * 100);
                  const col = score >= 0.65 ? '#ef4444' : score >= 0.35 ? '#f7b23b' : '#2dd96f';
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1 group" title={`${outlookLabels[i]}: ${Math.round(score * 100)}%`}>
                      <span className="font-data-mono text-[10px] text-on-surface-variant">{Math.round(score * 100)}%</span>
                      <div
                        className="w-full rounded-t-sm transition-all"
                        style={{ height: `${Math.max(pct * 1.2, 4)}px`, backgroundColor: col, opacity: 0.85 }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between">
                {outlookLabels.map((label, i) => (
                  <span key={i} className="font-label-caps text-[9px] text-on-surface-variant flex-1 text-center">{label}</span>
                ))}
              </div>
            </>
          )}
        </section>

        {/* Distance bucket chart */}
        <section className="bg-surface-container rounded-xl border border-outline-variant p-6 flex flex-col gap-4 shadow-sm">
          <h3 className="text-title-lg text-on-surface font-bold">Vessels by Distance Band</h3>
          <div className="flex items-end gap-3 h-[140px] mt-2">
            {buckets.map(({ label, vessels: bv }) => {
              const pct = Math.round((bv.length / maxBucket) * 100);
              const col = pct > 70 ? '#ef4444' : pct > 40 ? '#f7b23b' : '#2dd96f';
              return (
                <div key={label} className="flex-1 flex flex-col items-center gap-1 group" title={`${label}: ${bv.length} vessels`}>
                  <span className="font-data-mono text-[10px] text-on-surface-variant">{bv.length}</span>
                  <div
                    className="w-full rounded-t-sm transition-all"
                    style={{ height: `${Math.max(pct * 1.2, bv.length > 0 ? 4 : 0)}px`, backgroundColor: col, opacity: 0.8 }}
                  />
                  <span className="font-label-caps text-[9px] text-on-surface-variant text-center leading-tight">{label}</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Arrival queue from real schedule */}
        <section className="bg-surface-container rounded-xl border border-outline-variant p-6 flex flex-col gap-3 shadow-sm lg:col-span-2">
          <div className="flex justify-between items-center">
            <h3 className="text-title-lg text-on-surface font-bold">Arrival Queue</h3>
            <span className="font-label-caps text-label-caps text-on-surface-variant">{schedule.length} INBOUND</span>
          </div>
          <div className="flex flex-col gap-2 overflow-y-auto max-h-[240px]">
            {schedule.length === 0 ? (
              <p className="text-on-surface-variant font-body-sm text-center py-6">No vessels currently approaching.</p>
            ) : schedule.map((v, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-outline-variant/30 last:border-0">
                <div className="flex flex-col">
                  <span className="font-bold text-body-sm text-on-surface truncate max-w-[200px]">{v.vessel}</span>
                  <span className="font-data-mono text-[10px] text-on-surface-variant">{v.distance_nm} nm away · {v.sog} kts</span>
                </div>
                <span
                  className="font-data-mono text-[11px] text-primary"
                  title="Estimated ETA — heuristic from distance ÷ speed, not a model prediction"
                >
                  {v.eta || '--:--'} <span className="text-[9px] text-on-surface-variant">est.</span>
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
