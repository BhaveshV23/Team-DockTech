import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Login from "./pages/Login";
import SignupPage from "./pages/SignupPage";

import Dashboard from "./pages/Dashboard";
import CargoRequest from "./pages/CargoRequest";
import DecisionOverview from "./pages/DecisionOverview";

import FreightForecast from "./pages/FreightForecast";
import VesselOptions from "./pages/VesselOptions";
import CostAnalysis from "./pages/CostAnalysis";
import ScenariosRisk from "./pages/ScenariosRisk";
import Recommendation from "./pages/Recommendation";
import DecisionReport from "./pages/DecisionReport";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Authentication */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Main Dashboard */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Decision Workflow */}
        <Route
          path="/cargo-request"
          element={<CargoRequest />}
        />

        <Route
          path="/decision-overview"
          element={<DecisionOverview />}
        />

        <Route
          path="/freight-forecast"
          element={<FreightForecast />}
        />

        <Route
          path="/vessel-options"
          element={<VesselOptions />}
        />

        <Route
          path="/cost-analysis"
          element={<CostAnalysis />}
        />

        <Route
          path="/scenarios-risk"
          element={<ScenariosRisk />}
        />

        <Route
          path="/recommendation"
          element={<Recommendation />}
        />

        <Route
          path="/decision-report"
          element={<DecisionReport />}
        />

        {/* Default */}
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />

        {/* Unknown routes */}
        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;