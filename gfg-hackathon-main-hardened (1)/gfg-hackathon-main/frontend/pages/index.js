import { useState } from "react";
import { useRouter } from "next/router";
import { login, signup } from "../lib/api";

export default function Home() {
  const [mode, setMode] = useState("login");
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(orgName, email, password);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed");
      setLoading(false);
    }
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      padding: "20px",
      position: "relative"
    }}>
      <div className="glass-panel animate-enter" style={{ width: "100%", maxWidth: "440px" }}>

        {/* Logo and Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{ display: "inline-flex", padding: "12px", background: "rgba(139, 92, 246, 0.1)", borderRadius: "12px", marginBottom: "16px", border: "1px solid rgba(139, 92, 246, 0.2)" }}>
            <svg style={{ width: "32px", height: "32px", color: "#8b5cf6" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "6px" }}>
            SYSTEM<span style={{ color: "#8b5cf6" }}>SIEGE</span>
          </h1>
          <p style={{ fontSize: "12px", color: "var(--accent)", fontWeight: "600", letterSpacing: "1.5px", textTransform: "uppercase" }}>
            Web Sentinel Console
          </p>
        </div>

        {/* Tab Selection */}
        <div style={{ display: "flex", background: "rgba(0, 0, 0, 0.2)", borderRadius: "8px", padding: "4px", marginBottom: "24px", border: "1px solid rgba(255, 255, 255, 0.04)" }}>
          <button
            type="button"
            onClick={() => { setMode("login"); setError(""); }}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "6px", border: "none", cursor: "pointer", fontSize: "13px", fontWeight: "600",
              background: mode === "login" ? "var(--primary)" : "transparent",
              color: mode === "login" ? "#fff" : "var(--text-dim)",
              boxShadow: mode === "login" ? "0 2px 8px rgba(139, 92, 246, 0.3)" : "none",
              transition: "all 0.2s"
            }}>
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode("signup"); setError(""); }}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "6px", border: "none", cursor: "pointer", fontSize: "13px", fontWeight: "600",
              background: mode === "signup" ? "var(--primary)" : "transparent",
              color: mode === "signup" ? "#fff" : "var(--text-dim)",
              boxShadow: mode === "signup" ? "0 2px 8px rgba(139, 92, 246, 0.3)" : "none",
              transition: "all 0.2s"
            }}>
            Sign Up
          </button>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {mode === "signup" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-dim)", fontWeight: "500" }}>Organization Name</label>
              <div style={{ position: "relative" }}>
                <svg style={{ position: "absolute", left: "14px", top: "14px", width: "16px", height: "16px", color: "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <input
                  placeholder="e.g. Acme Cybersecurity"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                  style={{ paddingLeft: "42px" }}
                />
              </div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--text-dim)", fontWeight: "500" }}>Account Email</label>
            <div style={{ position: "relative" }}>
              <svg style={{ position: "absolute", left: "14px", top: "14px", width: "16px", height: "16px", color: "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
              </svg>
              <input
                placeholder="operator@systemsiege.com"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ paddingLeft: "42px" }}
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--text-dim)", fontWeight: "500" }}>Security Key / Password</label>
            <div style={{ position: "relative" }}>
              <svg style={{ position: "absolute", left: "14px", top: "14px", width: "16px", height: "16px", color: "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <input
                placeholder="••••••••••••"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                style={{ paddingLeft: "42px" }}
              />
            </div>
          </div>

          {error && (
            <div style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              padding: "12px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginTop: "8px"
            }}>
              <svg style={{ width: "16px", height: "16px", color: "var(--danger)", flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p style={{ color: "#fca5a5", fontSize: "12.5px" }}>{error}</p>
            </div>
          )}

          <button
            type="submit"
            className="btn"
            disabled={loading}
            style={{ width: "100%", marginTop: "12px" }}>
            {loading ? (
              <>
                <svg className="spinner" style={{ width: "18px", height: "18px" }} fill="none" viewBox="0 0 24 24">
                  <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Authenticating...
              </>
            ) : (
              mode === "login" ? "Access Sentinel console" : "Initialize Sentinel Organization"
            )}
          </button>
        </form>
      </div>

      {/* System Status Indicators at bottom */}
      <div style={{ marginTop: "24px", display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-muted)", fontWeight: "500" }}>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "6px", height: "6px", background: "var(--success)", borderRadius: "50%" }}></span>
          Core API: Connected
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "6px", height: "6px", background: "var(--accent)", borderRadius: "50%" }}></span>
          CORS Guard: Strict
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "6px", height: "6px", background: "var(--primary)", borderRadius: "50%" }}></span>
          JWT Secure: RS256
        </span>
      </div>
    </div>
  );
}
