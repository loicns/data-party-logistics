import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import OperationsDashboard from "./pages/OperationsDashboard";
import VesselTrafficMap from "./pages/VesselTrafficMap";
import ArrivalDepartureSchedule from "./pages/ArrivalDepartureSchedule";
import BerthSchedulingView from "./pages/BerthSchedulingView";
import CongestionInsights from "./pages/CongestionInsights";
import PredictiveAnalysis from "./pages/PredictiveAnalysis";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<OperationsDashboard />} />
          <Route path="map" element={<VesselTrafficMap />} />
          <Route path="schedule" element={<ArrivalDepartureSchedule />} />
          <Route path="berth" element={<BerthSchedulingView />} />
          <Route path="insights" element={<CongestionInsights />} />
          <Route path="predictive" element={<PredictiveAnalysis />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
