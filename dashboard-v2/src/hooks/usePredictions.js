import { useState, useEffect } from 'react';

// Derive the predictions URL from the SAME CloudFront base as the dashboard data,
// so it always sits next to demo-data and needs no extra env var.
//   VITE_DATA_URL = https://dxxxx.cloudfront.net/api/v1/demo-data.json
//        ->         https://dxxxx.cloudfront.net/api/v1/predictions.json
// In local dev (VITE_DATA_URL unset) -> /predictions.json (public/ fixture).
const DATA_URL = import.meta.env.VITE_DATA_URL ?? null;
const PREDICTIONS_URL = DATA_URL
  ? DATA_URL.replace(/demo-data\.json(\?.*)?$/, 'predictions.json$1')
  : '/predictions.json';

// Fetches predictions — a SEPARATE source from DataContext.
// Returns a map: { "NLRTM": { prediction, probability, as_of } | null }
export function usePredictions() {
  const [predictions, setPredictions] = useState(null);

  useEffect(() => {
    fetch(PREDICTIONS_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      // predict_lambda publishes { generatedAt, predictions: {...} };
      // the older committed file was a flat { PORT: {...} } — support both.
      .then((data) => setPredictions(data?.predictions ?? data ?? {}))
      .catch(() => setPredictions({})); // graceful: never white-screen
  }, []);

  return predictions;
}
