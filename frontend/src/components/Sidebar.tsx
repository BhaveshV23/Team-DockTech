import {
    AlertTriangle,
    BarChart3,
    FileText,
    LogOut,
    ShieldCheck,
    Ship,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { getRoleLabel, signOut, useAuthenticatedUser } from "../services/api";
import "./Sidebar.css";

type SidebarProps = {
    activePage:
    | "dashboard"
    | "cargo-request"
    | "decision-overview"
    | "freight-forecast"
    | "vessel-options"
    | "cost-analysis"
    | "scenarios-risk"
    | "recommendation"
    | "decision-report"
    | "admin-users";
};

function Sidebar({ activePage }: SidebarProps) {
    const navigate = useNavigate();
    const [signOutError, setSignOutError] = useState("");
    const user = useAuthenticatedUser();

    const handleSignOut = async () => {
        setSignOutError("");
        try {
            await signOut();
            navigate("/login", { replace: true });
        } catch (error) {
            setSignOutError(error instanceof Error ? error.message : "Unable to sign out.");
        }
    };

    return (
        <aside className="app-sidebar">
            <div className="app-sidebar-brand">
                <div className="app-sidebar-brand-icon">
                    <Ship size={22} />
                </div>

                <div>
                    <h2>DockTech</h2>
                    <span>Freight Intelligence</span>
                </div>
            </div>

            <nav className="app-sidebar-nav">
                <Link
                    to="/dashboard"
                    className={`app-sidebar-item ${activePage === "dashboard" ? "active" : ""
                        }`}
                >
                    <BarChart3 size={18} />
                    <span>Dashboard</span>
                </Link>

                <Link
                    to="/cargo-request"
                    className={`app-sidebar-item ${activePage === "cargo-request" ? "active" : ""
                        }`}
                >
                    <Ship size={18} />
                    <span>Cargo Request</span>
                </Link>

                <Link
                    to="/decision-overview"
                    className={`app-sidebar-item ${activePage === "decision-overview" ? "active" : ""
                        }`}
                >
                    <TrendingUp size={18} />
                    <span>Decision Overview</span>
                </Link>

                <Link
                    to="/freight-forecast"
                    className={`app-sidebar-item ${activePage === "freight-forecast" ? "active" : ""
                        }`}
                >
                    <TrendingUp size={18} />
                    <span>Freight Forecast</span>
                </Link>

                <Link
                    to="/vessel-options"
                    className={`app-sidebar-item ${activePage === "vessel-options" ? "active" : ""
                        }`}
                >
                    <Ship size={18} />
                    <span>Vessel Options</span>
                </Link>

                <Link
                    to="/cost-analysis"
                    className={`app-sidebar-item ${activePage === "cost-analysis" ? "active" : ""
                        }`}
                >
                    <BarChart3 size={18} />
                    <span>Cost Analysis</span>
                </Link>

                <Link
                    to="/scenarios-risk"
                    className={`app-sidebar-item ${activePage === "scenarios-risk" ? "active" : ""
                        }`}
                >
                    <AlertTriangle size={18} />
                    <span>Scenarios &amp; Risk</span>
                </Link>

                <Link
                    to="/recommendation"
                    className={`app-sidebar-item ${activePage === "recommendation" ? "active" : ""
                        }`}
                >
                    <TrendingUp size={18} />
                    <span>Recommendation</span>
                </Link>

                <Link
                    to="/decision-report"
                    className={`app-sidebar-item ${activePage === "decision-report" ? "active" : ""
                        }`}
                >
                    <FileText size={18} />
                    <span>Decision Report</span>
                </Link>

                {user?.role === "ADMINISTRATOR" && (
                    <Link
                        to="/admin/users"
                        className={`app-sidebar-item ${activePage === "admin-users" ? "active" : ""}`}
                    >
                        <ShieldCheck size={18} />
                        <span>User Roles</span>
                    </Link>
                )}

                <button
                    type="button"
                    className="app-sidebar-item"
                    onClick={handleSignOut}
                    style={{ width: "100%", border: 0, background: "transparent", color: "inherit", textAlign: "left", cursor: "pointer", font: "inherit" }}
                >
                    <LogOut size={18} />
                    <span>Sign out</span>
                </button>
            </nav>

            <div className="app-sidebar-footer">
                <span>DockTech v1.0</span>
                {signOutError && <span role="alert">{signOutError}</span>}
            </div>

            {user && (
                <div className="app-sidebar-profile" aria-label="Signed-in user">
                    <strong>{user.name}</strong>
                    <span>{getRoleLabel(user.role)}</span>
                </div>
            )}
        </aside>
    );
}

export default Sidebar;
