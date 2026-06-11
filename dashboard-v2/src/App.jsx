import { BrowserRouter, Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout";

// Route-level code splitting: heavy deps (maplibre-gl, chart.js) load only on
// the pages that use them, instead of blocking first paint everywhere.
const OperationsDashboard = lazy(() => import("./pages/OperationsDashboard"));
const VesselTrafficMap = lazy(() => import("./pages/VesselTrafficMap"));
const ArrivalDepartureSchedule = lazy(() => import("./pages/ArrivalDepartureSchedule"));
const BerthSchedulingView = lazy(() => import("./pages/BerthSchedulingView"));
const CongestionInsights = lazy(() => import("./pages/CongestionInsights"));
const PredictiveAnalysis = lazy(() => import("./pages/PredictiveAnalysis"));

function PageFallback() {
  return (
    <div className="flex items-center justify-center h-full min-h-[300px] text-on-surface-variant font-body-md">
      Loading…
    </div>
  );
}

function lazyRoute(Component) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Component />
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={lazyRoute(OperationsDashboard)} />
          <Route path="map" element={lazyRoute(VesselTrafficMap)} />
          <Route path="schedule" element={lazyRoute(ArrivalDepartureSchedule)} />
          <Route path="berth" element={lazyRoute(BerthSchedulingView)} />
          <Route path="insights" element={lazyRoute(CongestionInsights)} />
          <Route path="predictive" element={lazyRoute(PredictiveAnalysis)} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
