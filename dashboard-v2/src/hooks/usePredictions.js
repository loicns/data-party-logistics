import { useState, useEffect } from 'react';

// Derive the predictions URL from the SAME CloudFront base as the dashboard data,
// so it always sits next to demo-data and needs no extra env var.
//   VITE_DATA_URL = https://dxxxx.cloudfront.net/demo-data.js
//        ->         https://dxxxx.cloudfront.net/predictions.json
// The data artifact is published as demo-data.js (not .json), so match both
// extensions — otherwise the replace is a no-op and predictions never load.
// In local dev (VITE_DATA_URL unset) -> /predictions.json (public/ fixture).
const DATA_URL = import.meta.env.VITE_DATA_URL ?? null;
const PREDICTIONS_URL = DATA_URL
  ? DATA_URL.replace(/demo-data\.js(?:on)?(\?.*)?$/, 'predictions.json$1')
  : '/predictions.json';

// Fetches predictions — a SEPARATE source from DataContext.
// Returns a map: { "NLRTM": { prediction, probability, as_of } | null }
export function usePredictions() {
  const [predictions, setPredictions] = useState(null);

  useEffect(() => {
    fetch(PREDICTIONS_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Prediction fetch failed: ${r.status}`))))
      // predict_lambda publishes { generatedAt, predictions: {...} };
      // the older committed file was a flat { PORT: {...} } — support both.
      .then((data) => setPredictions(data?.predictions ?? data ?? {}))
      .catch((error) => {
        if (import.meta.env.DEV) {
          console.warn(error instanceof Error ? error.message : String(error));
        }
        setPredictions({});
      });
  }, []);

  return predictions;
}
