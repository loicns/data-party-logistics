import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout";

const OperationsDashboard = lazy(() => import("./pages/OperationsDashboard"));
const VesselTrafficMap = lazy(() => import("./pages/VesselTrafficMap"));
const ArrivalDepartureSchedule = lazy(() => import("./pages/ArrivalDepartureSchedule"));
const BerthSchedulingView = lazy(() => import("./pages/BerthSchedulingView"));
const CongestionInsights = lazy(() => import("./pages/CongestionInsights"));
const PredictiveAnalysis = lazy(() => import("./pages/PredictiveAnalysis"));
const RoadmapDashboard = lazy(() => import("./pages/RoadmapDashboard"));
const PhaseOneLanding = lazy(() => import("./pages/PhaseOneLanding"));

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
        <Route path="/" element={lazyRoute(PhaseOneLanding)} />
        <Route path="/phase-1" element={<Navigate to="/" replace />} />

        {/* Isolated Roadmap Dashboard Route */}
        <Route path="/roadmap" element={<Navigate to="/roadmap/overview" replace />} />
        <Route path="/roadmap/:view" element={lazyRoute(RoadmapDashboard)} />

        <Route path="/dashboard" element={<Layout />}>
          <Route index element={lazyRoute(OperationsDashboard)} />
          <Route path="map" element={lazyRoute(VesselTrafficMap)} />
          <Route path="schedule" element={lazyRoute(ArrivalDepartureSchedule)} />
          <Route path="berth" element={lazyRoute(BerthSchedulingView)} />
          <Route path="insights" element={lazyRoute(CongestionInsights)} />
          <Route path="predictive" element={lazyRoute(PredictiveAnalysis)} />
        </Route>

        <Route path="/map" element={<Navigate to="/dashboard/map" replace />} />
        <Route path="/schedule" element={<Navigate to="/dashboard/schedule" replace />} />
        <Route path="/berth" element={<Navigate to="/dashboard/berth" replace />} />
        <Route path="/insights" element={<Navigate to="/dashboard/insights" replace />} />
        <Route path="/predictive" element={<Navigate to="/dashboard/predictive" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
