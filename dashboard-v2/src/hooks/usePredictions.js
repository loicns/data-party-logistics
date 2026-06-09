import { useState, useEffect } from 'react';

// Fetches predictions.json — a SEPARATE source from DataContext.
// Shape: { "NLRTM": { prediction, probability, as_of } | null }
export function usePredictions() {
  const [predictions, setPredictions] = useState(null);

  useEffect(() => {
    fetch('/predictions.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setPredictions)
      .catch(() => setPredictions({})); // graceful: never white-screen
  }, []);

  return predictions;
}
