import { Link } from "react-router-dom";
import { useState } from 'react'
import {
    Anchor,
    BarChart3,
    CheckCircle2,
    Eye,
    EyeOff,
    ShieldCheck,
    Ship,
} from 'lucide-react'

import './Login.css'

function Login() {
    const [showPassword, setShowPassword] = useState(false)
    const [rememberMe, setRememberMe] = useState(false)

    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [role, setRole] = useState("")

    const [errors, setErrors] = useState<{
        email?: string
        password?: string
        role?: string
    }>({})

    const validateLogin = () => {
        const newErrors: {
            email?: string
            password?: string
            role?: string
        } = {}

        const trimmedEmail = email.trim()
        const trimmedPassword = password.trim()

        if (!trimmedEmail) {
            newErrors.email = "Email is required."
        } else if (
            !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)
        ) {
            newErrors.email = "Enter a valid email address."
        }

        if (!trimmedPassword) {
            newErrors.password = "Password is required."
        }

        if (!role) {
            newErrors.role = "Please select your role."
        }

        setErrors(newErrors)

        return Object.keys(newErrors).length === 0
    }
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
                            <span>Smarter Decisions. Safer Voyages. Stronger Tomorrow.</span>
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
          RIGHT LOGIN PANEL
      ========================================= */}

            <section className="login-panel">

                <div className="login-card">

                    <div className="login-heading">

                        <h2>Welcome Back</h2>

                        <p>
                            Sign in to your DockTech account
                        </p>

                    </div>


                    <form
                        className="login-form"
                        onSubmit={(event) => {
                            event.preventDefault()

                            if (validateLogin()) {
                                console.log("Login validation successful")
                            }
                        }}
                    >

                        {/* Email */}
                        <div className="form-field">

                            <label htmlFor="email">
                                Email
                            </label>

                            <input
                                id="email"
                                name="email"
                                type="email"
                                placeholder="you@example.com"
                                autoComplete="email"
                                value={email}
                                onChange={(event) => {
                                    setEmail(event.target.value)

                                    if (errors.email) {
                                        setErrors((current) => ({
                                            ...current,
                                            email: undefined,
                                        }))
                                    }
                                }}
                            />

                            {errors.email && (
                                <span className="field-error">
                                    {errors.email}
                                </span>
                            )}

                        </div>


                        {/* Password */}
                        <div className="form-field">

                            <label htmlFor="password">
                                Password
                            </label>

                            <div className="password-wrapper">

                                <input
                                    id="password"
                                    name="password"
                                    type={showPassword ? "text" : "password"}
                                    placeholder="Enter your password"
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={(event) => {
                                        setPassword(event.target.value)

                                        if (errors.password) {
                                            setErrors((current) => ({
                                                ...current,
                                                password: undefined,
                                            }))
                                        }
                                    }}
                                />

                                <button
                                    type="button"
                                    className="password-toggle"
                                    aria-label={
                                        showPassword
                                            ? 'Hide password'
                                            : 'Show password'
                                    }
                                    onClick={() =>
                                        setShowPassword((current) => !current)
                                    }
                                >
                                    {showPassword ? (
                                        <EyeOff size={17} />
                                    ) : (
                                        <Eye size={17} />
                                    )}
                                </button>

                            </div>

                            {/* ADD THE ERROR HERE */}
                            {errors.password && (
                                <span className="field-error">
                                    {errors.password}
                                </span>
                            )}

                        </div>

                        <div className="form-field">
                            <label htmlFor="role">
                                Role
                            </label>

                            <select
                                id="role"
                                name="role"
                                value={role}
                                onChange={(event) => {
                                    setRole(event.target.value)

                                    if (errors.role) {
                                        setErrors((current) => ({
                                            ...current,
                                            role: undefined,
                                        }))
                                    }
                                }}
                            >
                                <option value="" disabled>
                                    Select your role
                                </option>

                                <option value="VIEWER">Viewer</option>
                                <option value="PLANNER">Planner</option>
                                <option value="MANAGER">Manager</option>
                                <option value="ADMINISTRATOR">Administrator</option>
                            </select>

                            {errors.role && (
                                <span className="field-error">
                                    {errors.role}
                                </span>
                            )}
                        </div>


                        {/* Remember / Forgot */}
                        <div className="login-options">

                            <label className="remember-option">

                                <input
                                    type="checkbox"
                                    checked={rememberMe}
                                    onChange={(event) =>
                                        setRememberMe(event.target.checked)
                                    }
                                />

                                <span>Remember me</span>

                            </label>

                            <button
                                type="button"
                                className="forgot-password"
                            >
                                Forgot password?
                            </button>

                        </div>


                        {/* Sign in */}
                        <button
                            type="submit"
                            className="login-button"
                        >
                            Sign In
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
                            Sign in with SSO (Supabase)
                        </span>

                    </button>

                    <div className="signup-link">
                        Don't have an account?{" "}
                        <Link to="/signup">Sign up</Link>
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
    )
}

export default Login
