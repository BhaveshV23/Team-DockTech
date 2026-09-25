import { useState } from "react";
import type { FormEvent } from "react";
import {
    Anchor,
    BarChart3,
    CheckCircle2,
    Eye,
    EyeOff,
    ShieldCheck,
    Ship,
} from "lucide-react";
import { Link } from "react-router-dom";

import "./Login.css";

function SignupPage() {
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        // Supabase authentication will be added later.
        console.log("Signup form submitted");
    };

    return (
        <main className="login-page">

            {/* =========================================
                LEFT BRAND PANEL
            ========================================= */}

            <section className="login-brand">

                <div className="login-brand-overlay" />

                <div className="login-brand-content">

                    {/* Top branding */}
                    <header className="brand-header">

                        <div className="brand-logo">
                            <span className="brand-wave">≈</span>
                        </div>

                        <div className="brand-name">
                            <strong>DockTech</strong>
                            <span>
                                Smarter Decisions. Safer Voyages. Stronger Tomorrow.
                            </span>
                        </div>

                        <span className="brand-location">
                            India's East Coast. Global Opportunities.
                        </span>

                    </header>

                    {/* Main message */}
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

                    {/* Product capabilities */}
                    <div className="brand-capabilities">

                        <div className="capability">
                            <BarChart3 size={22} strokeWidth={1.8} />
                            <span>Freight Forecasting</span>
                        </div>

                        <div className="capability">
                            <Ship size={22} strokeWidth={1.8} />
                            <span>Vessel Feasibility</span>
                        </div>

                        <div className="capability">
                            <Anchor size={22} strokeWidth={1.8} />
                            <span>Cost Comparison</span>
                        </div>

                        <div className="capability">
                            <ShieldCheck size={22} strokeWidth={1.8} />
                            <span>Risk Analysis</span>
                        </div>

                    </div>

                </div>

            </section>


            {/* =========================================
                RIGHT SIGN UP PANEL
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
                                required
                            />

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
                                required
                            />

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
                                            (current) => !current
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
                                            (current) => !current
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

                        </div>


                        {/* Role */}
                        <div className="form-field">

                            <label htmlFor="signup-role">
                                Role
                            </label>

                            <select
                                id="signup-role"
                                name="role"
                                defaultValue=""
                                required
                            >
                                <option value="" disabled>
                                    Select your role
                                </option>

                                <option value="VIEWER">
                                    Viewer
                                </option>

                                <option value="PLANNER">
                                    Planner
                                </option>

                                <option value="MANAGER">
                                    Manager
                                </option>

                                <option value="ADMINISTRATOR">
                                    Administrator
                                </option>

                            </select>

                        </div>


                        {/* Create Account */}
                        <button
                            type="submit"
                            className="login-button"
                        >
                            Create Account
                        </button>

                    </form>


                    {/* Divider */}
                    <div className="login-divider">

                        <span />

                        <small>or</small>

                        <span />

                    </div>


                    {/* SSO */}
                    <button
                        type="button"
                        className="sso-button"
                    >

                        <CheckCircle2
                            size={17}
                            strokeWidth={2}
                        />

                        <span>
                            Sign up with SSO (Supabase)
                        </span>

                    </button>


                    {/* Login Link */}
                    <div className="signup-link">

                        Already have an account?{" "}

                        <Link to="/login">
                            Sign in
                        </Link>

                    </div>


                    {/* Footer */}
                    <div className="login-footer">

                        <span>DockTech v1.0</span>

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