import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";

import { apiRequest, getAuthConfigurationError, setAuthenticatedProfile, supabase } from "./services/api";
import type { AuthProfile } from "./services/api";
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

type AuthState = {
  status: "loading" | "authenticated" | "unauthenticated";
};

const AuthContext = createContext<AuthState>({
  status: "loading",
});

function ProtectedRoutes() {
  const { status } = useContext(AuthContext);
  if (status === "loading") {
    return <main role="status" aria-live="polite">Checking your session…</main>;
  }
  return status === "authenticated"
    ? <Outlet />
    : <Navigate to="/login" replace />;
}

function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({
    status: supabase ? "loading" : "unauthenticated",
  });

  useEffect(() => {
    let active = true;
    let validation = 0;

    const resolveSession = async (session: Session | null) => {
      const currentValidation = ++validation;
      if (!session) {
        setAuthenticatedProfile(null);
        if (active) setAuth({ status: "unauthenticated" });
        return;
      }

      if (active) setAuth({ status: "loading" });
      try {
        const profile = await apiRequest<AuthProfile>("/api/v1/auth/provision", {
          method: "POST",
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (active && currentValidation === validation) {
          setAuthenticatedProfile(profile);
          setAuth({ status: "authenticated" });
        }
      } catch {
        if (active && currentValidation === validation) {
          setAuthenticatedProfile(null);
          setAuth({ status: "unauthenticated" });
        }
      }
    };

    if (!supabase) {
      return () => { active = false; };
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => { void resolveSession(session); },
    );
    void supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) {
        setAuthenticatedProfile(null);
        setAuth({ status: "unauthenticated" });
      }
      else void resolveSession(data.session);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

function App() {
  const configurationError = getAuthConfigurationError();
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route element={<ProtectedRoutes />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/cargo-request" element={<CargoRequest />} />
            <Route path="/decision-overview" element={<DecisionOverview />} />
            <Route path="/freight-forecast" element={<FreightForecast />} />
            <Route path="/vessel-options" element={<VesselOptions />} />
            <Route path="/cost-analysis" element={<CostAnalysis />} />
            <Route path="/scenarios-risk" element={<ScenariosRisk />} />
            <Route path="/recommendation" element={<Recommendation />} />
            <Route path="/decision-report" element={<DecisionReport />} />
          </Route>
          <Route path="/" element={<Navigate to={configurationError ? "/login" : "/dashboard"} replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
