import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";

import { apiRequest, getAuthConfigurationError, setAuthenticatedProfile, setCurrentAccessToken, supabase, useAuthenticatedUser } from "./services/api";
import type { AuthProfile } from "./services/api";
import { WorkflowStateProvider } from "./context/WorkflowStateContext";
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
import AdminUserRoles from "./pages/AdminUserRoles";

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
  const initialAuth: AuthState = {
    status: supabase ? "loading" : "unauthenticated",
  };
  const [auth, setAuth] = useState<AuthState>(initialAuth);
  const authRef = useRef<AuthState>(initialAuth);
  const authUserIdRef = useRef<string | null>(null);

  const updateAuth = (nextAuth: AuthState) => {
    authRef.current = nextAuth;
    setAuth(nextAuth);
  };

  useEffect(() => {
    let active = true;
    const resolveSession = async (event: string, session: Session | null) => {
      setCurrentAccessToken(session?.access_token ?? null);

      if (!session) {
        authUserIdRef.current = null;
        setAuthenticatedProfile(null);
        if (active && authRef.current.status !== "unauthenticated") {
          updateAuth({ status: "unauthenticated" });
        }
        return;
      }

      const authUserId = session.user.id;
      const sameIdentity = authUserIdRef.current === authUserId;

      // Refreshing the access token does not change who is signed in. Keep the
      // current profile and UI while refreshing it in the background.
      if (event === "TOKEN_REFRESHED") {
        if (sameIdentity && authRef.current.status === "authenticated") {
          void apiRequest<AuthProfile>("/api/v1/auth/provision", {
            method: "POST",
            headers: { Authorization: `Bearer ${session.access_token}` },
          }).then((profile) => {
            if (active && authUserIdRef.current === authUserId) {
              setAuthenticatedProfile(profile);
            }
          }).catch(() => {
            // A transient profile refresh failure must not interrupt a valid session.
          });
        }
        return;
      }

      if (sameIdentity && authRef.current.status === "authenticated") return;

      authUserIdRef.current = authUserId;
      setAuthenticatedProfile(null);
      if (active && authRef.current.status !== "loading") {
        updateAuth({ status: "loading" });
      }

      try {
        const profile = await apiRequest<AuthProfile>("/api/v1/auth/provision", {
          method: "POST",
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (active && authUserIdRef.current === authUserId) {
          setAuthenticatedProfile(profile);
          updateAuth({ status: "authenticated" });
        }
      } catch {
        if (active && authUserIdRef.current === authUserId) {
          setAuthenticatedProfile(null);
          authUserIdRef.current = null;
          updateAuth({ status: "unauthenticated" });
        }
      }
    };

    if (!supabase) {
      return () => { active = false; };
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => { void resolveSession(event, session); },
    );

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

function AppRoutes({ configurationError }: { configurationError: string | null }) {
  const user = useAuthenticatedUser();
  const authenticatedUserId = user?.user_id ?? null;
  return (
    <WorkflowStateProvider key={authenticatedUserId ?? "unauthenticated"} authenticatedUserId={authenticatedUserId}>
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
          <Route path="/admin/users" element={<AdminUserRoles />} />
        </Route>
        <Route path="/" element={<Navigate to={configurationError ? "/login" : "/dashboard"} replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </WorkflowStateProvider>
  );
}

function App() {
  const configurationError = getAuthConfigurationError();
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes configurationError={configurationError} />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
