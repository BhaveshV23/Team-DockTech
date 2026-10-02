import { useState } from "react";
import type { FormEvent } from "react";
import {
    Anchor,
    BarChart3,
    Eye,
    EyeOff,
    ShieldCheck,
    Ship,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { apiRequest, getAuthConfigurationError, setAuthenticatedProfile, supabase } from "../services/api";
import type { AuthProfile } from "../services/api";

import "./Login.css";

function SignupPage() {
    // =========================================
    // FORM STATE
    // =========================================

    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [serverError, setServerError] = useState("");
    const [notice, setNotice] = useState("");
    const navigate = useNavigate();

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] =
        useState(false);

    const [errors, setErrors] = useState<{
        fullName?: string;
        email?: string;
        password?: string;
        confirmPassword?: string;
    }>({});


    // =========================================
    // SIGNUP VALIDATION
    // =========================================

    const validateSignup = () => {
        const newErrors: {
            fullName?: string;
            email?: string;
            password?: string;
            confirmPassword?: string;
        } = {};

        const trimmedFullName = fullName.trim();
        const trimmedEmail = email.trim();
        const trimmedPassword = password;
        const trimmedConfirmPassword = confirmPassword;


        // Full Name
        if (!trimmedFullName) {
            newErrors.fullName =
                "Full name is required.";
        }


        // Email
        if (!trimmedEmail) {
            newErrors.email =
                "Email is required.";
        } else if (
            !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
                trimmedEmail
            )
        ) {
            newErrors.email =
                "Enter a valid email address.";
        }


        // Password
        if (!trimmedPassword) {
            newErrors.password =
                "Password is required.";
        } else if (trimmedPassword.length < 8) {
            newErrors.password =
                "Password must contain at least 8 characters.";
        } else if (!/[A-Z]/.test(trimmedPassword)) {
            newErrors.password =
                "Password must contain at least one uppercase letter.";
        } else if (!/[a-z]/.test(trimmedPassword)) {
            newErrors.password =
                "Password must contain at least one lowercase letter.";
        } else if (!/[0-9]/.test(trimmedPassword)) {
            newErrors.password =
                "Password must contain at least one digit.";
        } else if (
            !/[^A-Za-z0-9]/.test(trimmedPassword)
        ) {
            newErrors.password =
                "Password must contain at least one special character.";
        }


        // Confirm Password
        if (!trimmedConfirmPassword) {
            newErrors.confirmPassword =
                "Please confirm your password.";
        } else if (
            trimmedPassword !==
            trimmedConfirmPassword
        ) {
            newErrors.confirmPassword =
                "Passwords do not match.";
        }


        setErrors(newErrors);

        return Object.keys(newErrors).length === 0;
    };


    // =========================================
    // FORM SUBMIT
    // =========================================

    const handleSubmit = async (
        event: FormEvent<HTMLFormElement>
    ) => {
        event.preventDefault();
        setServerError("");
        setNotice("");
        if (!validateSignup()) return;
        if (!supabase) {
            setServerError(getAuthConfigurationError() ?? "Authentication is unavailable.");
            return;
        }

        setLoading(true);
        try {
            const { data, error } = await supabase.auth.signUp({
                email: email.trim(),
                password,
                options: { data: { display_name: fullName.trim() } },
            });
            if (error) throw new Error(error.message);
            if (!data.session) {
                setNotice("Account created. Confirm your email before signing in. Your DockTech profile will be created when you sign in.");
                return;
            }

            const profile = await apiRequest<AuthProfile>("/api/v1/auth/provision", {
                method: "POST",
                headers: { Authorization: `Bearer ${data.session.access_token}` },
            });
            setAuthenticatedProfile(profile);
            navigate("/dashboard", { replace: true });
        } catch (error) {
            await supabase.auth.signOut();
            setServerError(error instanceof Error ? error.message : "Unable to create your account.");
        } finally {
            setLoading(false);
        }
    };


    // =========================================
    // UI
    // =========================================

    return (
        <main className="login-page">

            {/* =========================================
                LEFT BRAND PANEL
            ========================================= */}

            <section className="login-brand">

                <div className="login-brand-overlay" />

                <div className="login-brand-content">

                    <header className="brand-header">

                        <div className="brand-logo">
                            <span className="brand-wave">
                                ≈
                            </span>
                        </div>

                        <div className="brand-name">
                            <strong>DockTech</strong>

                            <span>
                                Smarter Decisions. Safer Voyages.
                                Stronger Tomorrow.
                            </span>
                        </div>

                        <span className="brand-location">
                            India's East Coast. Global Opportunities.
                        </span>

                    </header>


                    <div className="brand-message">

                        <p className="brand-eyebrow">
                            FREIGHT INTELLIGENCE PLATFORM
                        </p>

                        <h1>
                            Intelligent Freight Forecasting &amp;
                            <br />
                            Chartering Decision Support System
                        </h1>

                        <p className="brand-subtitle">
                            Forecast. Evaluate. Compare. Decide.
                        </p>

                    </div>


                    <div className="brand-capabilities">

                        <div className="capability">
                            <BarChart3
                                size={22}
                                strokeWidth={1.8}
                            />
                            <span>
                                Freight Forecasting
                            </span>
                        </div>

                        <div className="capability">
                            <Ship
                                size={22}
                                strokeWidth={1.8}
                            />
                            <span>
                                Vessel Feasibility
                            </span>
                        </div>

                        <div className="capability">
                            <Anchor
                                size={22}
                                strokeWidth={1.8}
                            />
                            <span>
                                Cost Comparison
                            </span>
                        </div>

                        <div className="capability">
                            <ShieldCheck
                                size={22}
                                strokeWidth={1.8}
                            />
                            <span>
                                Risk Analysis
                            </span>
                        </div>

                    </div>

                </div>

            </section>


            {/* =========================================
                RIGHT SIGNUP PANEL
            ========================================= */}

            <section className="login-panel">

                <div className="login-card">

                    <div className="login-heading">

                        <h2>Create Account</h2>

                        <p>
                            Create your DockTech account
                        </p>

                    </div>


                    <form
                        className="login-form"
                        onSubmit={handleSubmit}
                    >

                        {/* Full Name */}
                        <div className="form-field">

                            <label htmlFor="fullName">
                                Full Name
                            </label>

                            <input
                                id="fullName"
                                name="fullName"
                                type="text"
                                placeholder="Enter your full name"
                                autoComplete="name"
                                value={fullName}
                                onChange={(event) => {
                                    setFullName(
                                        event.target.value
                                    );

                                    if (errors.fullName) {
                                        setErrors((current) => ({
                                            ...current,
                                            fullName: undefined,
                                        }));
                                    }
                                }}
                                required
                            />

                            {errors.fullName && (
                                <span className="field-error">
                                    {errors.fullName}
                                </span>
                            )}

                        </div>


                        {/* Email */}
                        <div className="form-field">

                            <label htmlFor="signup-email">
                                Email
                            </label>

                            <input
                                id="signup-email"
                                name="email"
                                type="email"
                                placeholder="you@example.com"
                                autoComplete="email"
                                value={email}
                                onChange={(event) => {
                                    setEmail(
                                        event.target.value
                                    );

                                    if (errors.email) {
                                        setErrors((current) => ({
                                            ...current,
                                            email: undefined,
                                        }));
                                    }
                                }}
                                required
                            />

                            {errors.email && (
                                <span className="field-error">
                                    {errors.email}
                                </span>
                            )}

                        </div>


                        {/* Password */}
                        <div className="form-field">

                            <label htmlFor="signup-password">
                                Password
                            </label>

                            <div className="password-wrapper">

                                <input
                                    id="signup-password"
                                    name="password"
                                    type={
                                        showPassword
                                            ? "text"
                                            : "password"
                                    }
                                    placeholder="Create a password"
                                    autoComplete="new-password"
                                    value={password}
                                    onChange={(event) => {
                                        setPassword(
                                            event.target.value
                                        );

                                        if (errors.password) {
                                            setErrors((current) => ({
                                                ...current,
                                                password: undefined,
                                            }));
                                        }
                                    }}
                                    required
                                />

                                <button
                                    type="button"
                                    className="password-toggle"
                                    aria-label={
                                        showPassword
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                    onClick={() =>
                                        setShowPassword(
                                            (current) =>
                                                !current
                                        )
                                    }
                                >
                                    {showPassword ? (
                                        <EyeOff size={17} />
                                    ) : (
                                        <Eye size={17} />
                                    )}
                                </button>

                            </div>

                            {errors.password && (
                                <span className="field-error">
                                    {errors.password}
                                </span>
                            )}

                        </div>


                        {/* Confirm Password */}
                        <div className="form-field">

                            <label htmlFor="confirm-password">
                                Confirm Password
                            </label>

                            <div className="password-wrapper">

                                <input
                                    id="confirm-password"
                                    name="confirmPassword"
                                    type={
                                        showConfirmPassword
                                            ? "text"
                                            : "password"
                                    }
                                    placeholder="Confirm your password"
                                    autoComplete="new-password"
                                    value={confirmPassword}
                                    onChange={(event) => {
                                        setConfirmPassword(
                                            event.target.value
                                        );

                                        if (
                                            errors.confirmPassword
                                        ) {
                                            setErrors((current) => ({
                                                ...current,
                                                confirmPassword:
                                                    undefined,
                                            }));
                                        }
                                    }}
                                    required
                                />

                                <button
                                    type="button"
                                    className="password-toggle"
                                    aria-label={
                                        showConfirmPassword
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                    onClick={() =>
                                        setShowConfirmPassword(
                                            (current) =>
                                                !current
                                        )
                                    }
                                >
                                    {showConfirmPassword ? (
                                        <EyeOff size={17} />
                                    ) : (
                                        <Eye size={17} />
                                    )}
                                </button>

                            </div>

                            {errors.confirmPassword && (
                                <span className="field-error">
                                    {errors.confirmPassword}
                                </span>
                            )}

                        </div>


                        {/* Create Account */}
                        <button
                            type="submit"
                            className="login-button"
                            disabled={loading}
                        >
                            {loading ? "Creating Account…" : "Create Account"}
                        </button>

                        {serverError && <div className="field-error" role="alert">{serverError}</div>}
                        {notice && <div role="status" aria-live="polite">{notice}</div>}

                    </form>


                    {/* Login Link */}
                    <div className="signup-link">

                        Already have an account?{" "}

                        <Link to="/login">
                            Sign in
                        </Link>

                    </div>


                    {/* Footer */}
                    <div className="login-footer">

                        <span>
                            DockTech v1.0
                        </span>

                        <span className="footer-separator">
                            |
                        </span>

                        <span>
                            Decision Support for a Stronger Tomorrow
                        </span>

                    </div>

                </div>

            </section>

        </main>
    );
}

export default SignupPage;
