import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw, ShieldCheck, Users } from "lucide-react";
import Sidebar from "../components/Sidebar";
import StatusMessage from "../components/StatusMessage";
import { apiRequest, useAuthenticatedUser } from "../services/api";
import type { AuthProfile } from "../services/api";
import "./AdminUserRoles.css";

type UserRole = AuthProfile["role"];
type UserSummary = Pick<AuthProfile, "user_id" | "display_name" | "email" | "role">;
type PageState =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "empty" }
    | { status: "ready"; users: UserSummary[] };

const roles: UserRole[] = ["VIEWER", "PLANNER", "MANAGER", "ADMINISTRATOR"];

function AdminUserRoles() {
    const user = useAuthenticatedUser();
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>({ status: "loading" });
    const [selectedRoles, setSelectedRoles] = useState<Record<string, UserRole>>({});
    const [updatingUsers, setUpdatingUsers] = useState<Set<string>>(() => new Set());
    const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
    const [notice, setNotice] = useState("");

    useEffect(() => {
        if (user?.role !== "ADMINISTRATOR") {
            setPageState({ status: "empty" });
            return;
        }

        let active = true;
        setPageState({ status: "loading" });
        void apiRequest<UserSummary[]>("/api/v1/auth/users")
            .then((profiles) => {
                if (!active) return;
                setSelectedRoles(Object.fromEntries(profiles.map((profile) => [profile.user_id, profile.role])));
                setPageState(profiles.length ? { status: "ready", users: profiles } : { status: "empty" });
            })
            .catch((error: unknown) => {
                if (!active) return;
                setPageState({
                    status: "error",
                    message: error instanceof Error ? error.message : "Unable to load user profiles.",
                });
            });

        return () => { active = false; };
    }, [retryCount, user?.role]);

    const updateRole = async (profile: UserSummary) => {
        const role = selectedRoles[profile.user_id];
        if (!role || role === profile.role || updatingUsers.has(profile.user_id)) return;

        setUpdatingUsers((current) => new Set(current).add(profile.user_id));
        setRowErrors((current) => ({ ...current, [profile.user_id]: "" }));
        setNotice("");
        try {
            const updatedProfile = await apiRequest<AuthProfile>(
                `/api/v1/auth/users/${encodeURIComponent(profile.user_id)}/role`,
                { method: "PATCH", body: JSON.stringify({ role }) },
            );
            const updated: UserSummary = {
                user_id: updatedProfile.user_id,
                display_name: updatedProfile.display_name,
                email: updatedProfile.email,
                role: updatedProfile.role,
            };
            setPageState((current) => current.status === "ready"
                ? { ...current, users: current.users.map((item) => item.user_id === updated.user_id ? updated : item) }
                : current);
            setSelectedRoles((current) => ({ ...current, [updated.user_id]: updated.role }));
            setNotice(`Role updated for ${updated.display_name}.`);
        } catch (error) {
            setRowErrors((current) => ({
                ...current,
                [profile.user_id]: error instanceof Error ? error.message : "Unable to update this user's role.",
            }));
        } finally {
            setUpdatingUsers((current) => {
                const next = new Set(current);
                next.delete(profile.user_id);
                return next;
            });
        }
    };

    if (user?.role !== "ADMINISTRATOR") {
        return (
            <div className="admin-users-page">
                <Sidebar activePage="admin-users" />
                <main className="admin-users-main">
                    <StatusMessage
                        type="error"
                        title="Administrator access required"
                        message="Your account does not have permission to manage user roles."
                    />
                </main>
            </div>
        );
    }

    return (
        <div className="admin-users-page">
            <Sidebar activePage="admin-users" />
            <main className="admin-users-main">
                <header className="admin-users-header">
                    <div>
                        <span className="admin-users-eyebrow">ACCESS MANAGEMENT</span>
                        <h1>User Roles</h1>
                        <p>Review application profiles and update their assigned roles.</p>
                    </div>
                    <span className="admin-users-status"><ShieldCheck size={15} /> Administrator</span>
                </header>

                <section className="admin-users-card" aria-labelledby="admin-users-list-title">
                    <div className="admin-users-card-heading">
                        <div className="admin-users-card-icon"><Users size={19} /></div>
                        <div>
                            <h2 id="admin-users-list-title">Application Users</h2>
                            <p>Role changes are applied by the DockTech backend.</p>
                        </div>
                    </div>

                    {pageState.status === "loading" && (
                        <StatusMessage type="loading" title="Loading users" message="Retrieving application profiles…" />
                    )}
                    {pageState.status === "error" && (
                        <div className="admin-users-error-block">
                            <StatusMessage type="error" title="Users unavailable" message={pageState.message} />
                            <button type="button" className="admin-users-secondary-button" onClick={() => setRetryCount((count) => count + 1)}>
                                <RefreshCw size={15} /> Retry
                            </button>
                        </div>
                    )}
                    {pageState.status === "empty" && (
                        <StatusMessage type="empty" title="No users found" message="There are no application profiles to display." />
                    )}
                    {pageState.status === "ready" && (
                        <>
                            {notice && <p className="admin-users-success" role="status"><CheckCircle2 size={16} />{notice}</p>}
                            <div className="admin-users-table-wrap">
                                <table className="admin-users-table">
                                    <thead>
                                        <tr>
                                            <th scope="col">Display Name</th>
                                            <th scope="col">Email</th>
                                            <th scope="col">Current Role</th>
                                            <th scope="col">Role selector</th>
                                            <th scope="col"><span className="visually-hidden">Update action</span></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {pageState.users.map((profile) => {
                                            const isSelf = profile.user_id === user.user_id;
                                            const isUpdating = updatingUsers.has(profile.user_id);
                                            const hasRoleChange = selectedRoles[profile.user_id] !== profile.role;
                                            return (
                                                <tr key={profile.user_id}>
                                                    <td data-label="Display Name">{profile.display_name}</td>
                                                    <td data-label="Email">{profile.email}</td>
                                                    <td data-label="Current Role"><span className="admin-users-role-badge">{profile.role}</span></td>
                                                    <td data-label="Role selector">
                                                        <select
                                                            aria-label={`Role for ${profile.display_name}`}
                                                            value={selectedRoles[profile.user_id] ?? profile.role}
                                                            disabled={isSelf || isUpdating}
                                                            onChange={(event) => setSelectedRoles((current) => ({
                                                                ...current,
                                                                [profile.user_id]: event.target.value as UserRole,
                                                            }))}
                                                        >
                                                            {roles.map((role) => <option key={role} value={role}>{role}</option>)}
                                                        </select>
                                                        {isSelf && <small className="admin-users-self-note">Your own role cannot be changed here.</small>}
                                                    </td>
                                                    <td data-label="Update action">
                                                        <button
                                                            type="button"
                                                            className="admin-users-primary-button"
                                                            disabled={isSelf || isUpdating || !hasRoleChange}
                                                            onClick={() => void updateRole(profile)}
                                                        >
                                                            {isUpdating ? <><RefreshCw className="admin-users-spinner" size={15} /> Updating</> : "Update"}
                                                        </button>
                                                        {rowErrors[profile.user_id] && <span className="admin-users-row-error" role="alert"><AlertCircle size={14} />{rowErrors[profile.user_id]}</span>}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </section>
            </main>
        </div>
    );
}

export default AdminUserRoles;
