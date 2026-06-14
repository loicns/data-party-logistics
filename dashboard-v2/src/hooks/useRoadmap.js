import { useEffect, useState } from 'react';

const DATA_URL = import.meta.env.VITE_DATA_URL ?? null;
const EXPLICIT_ROADMAP_URL = import.meta.env.VITE_ROADMAP_URL ?? null;
const FALLBACK_ROADMAP_URL = '/roadmap.json';

function roadmapUrlFromDataUrl(dataUrl) {
  return dataUrl.replace(/demo-data\.js(?:on)?(\?.*)?$/, 'roadmap.json$1');
}

function resolveRoadmapUrl() {
  if (EXPLICIT_ROADMAP_URL) return EXPLICIT_ROADMAP_URL;
  if (!DATA_URL) return FALLBACK_ROADMAP_URL;

  if (!import.meta.env.PROD || typeof window === 'undefined') {
    return roadmapUrlFromDataUrl(DATA_URL);
  }

  try {
    const target = new URL(DATA_URL, window.location.origin);
    if (target.origin !== window.location.origin) return '/live-roadmap.json';
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn(`Ignoring invalid VITE_DATA_URL for roadmap: ${String(error)}`);
    }
  }

  return roadmapUrlFromDataUrl(DATA_URL);
}

async function fetchRoadmap(primaryUrl) {
  const urls = primaryUrl === FALLBACK_ROADMAP_URL
    ? [FALLBACK_ROADMAP_URL]
    : [primaryUrl, FALLBACK_ROADMAP_URL];

  let lastError = null;
  for (const url of urls) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Roadmap fetch failed: ${response.status}`);
      return await response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error('Roadmap fetch failed');
}

export function useRoadmap() {
  const [state, setState] = useState({
    roadmap: null,
    loading: true,
    error: null,
    url: resolveRoadmapUrl(),
  });

  useEffect(() => {
    let cancelled = false;
    const url = resolveRoadmapUrl();

    fetchRoadmap(url)
      .then((roadmap) => {
        if (!cancelled) {
          setState({ roadmap, loading: false, error: null, url });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ roadmap: null, loading: false, error, url });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
