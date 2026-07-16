import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { apiFetch, setToken } from "../lib/api";

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [sites, setSites] = useState([]);
  const [selectedSite, setSelectedSite] = useState(null);
  const [alerts, setAlerts] = useState({}); // siteId -> alerts list
  const [auditLogs, setAuditLogs] = useState([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const [scanningSiteId, setScanningSiteId] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    loadUserAndSites();
  }, []);

  async function loadUserAndSites() {
    try {
      const u = await apiFetch("/api/auth/me");
      setUser(u);
      const sList = await apiFetch("/api/sites");
      setSites(sList);
      if (sList.length > 0) {
        setSelectedSite(sList[0]);
        loadAlerts(sList[0].id);
      }
      if (u.role === "owner" || u.role === "admin") {
        loadAuditLogs();
      }
    } catch (err) {
      // authentication failed or not logged in, redirect home
      router.push("/");
    }
  }

  async function loadSitesOnly() {
    try {
      const sList = await apiFetch("/api/sites");
      setSites(sList);
      return sList;
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadAlerts(siteId) {
    try {
      const siteAlerts = await apiFetch(`/api/sites/${siteId}/alerts`);
      setAlerts(prev => ({ ...prev, [siteId]: siteAlerts }));
    } catch (err) {
      setError("Failed to load alerts for site: " + err.message);
    }
  }

  async function loadAuditLogs() {
    try {
      const logs = await apiFetch("/api/audit-logs");
      setAuditLogs(logs);
    } catch (err) {
      console.error("Audit log loading failed:", err);
    }
  }

  async function addSite(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const newSite = await apiFetch("/api/sites", {
        method: "POST",
        body: JSON.stringify({ name, url }),
      });
      setName("");
      setUrl("");
      const updatedList = await loadSitesOnly();
      setSelectedSite(newSite);
      loadAlerts(newSite.id);
      if (user?.role === "owner" || user?.role === "admin") {
        loadAuditLogs();
      }
    } catch (err) {
      setError(err.message || "Failed to add site");
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteSite(siteId, e) {
    e.stopPropagation();
    if (!confirm("Are you sure you want to remove this site from Web Sentinel?")) return;
    setError("");
    try {
      await apiFetch(`/api/sites/${siteId}`, { method: "DELETE" });
      const updatedList = await loadSitesOnly();
      if (selectedSite?.id === siteId) {
        const nextSite = updatedList.length > 0 ? updatedList[0] : null;
        setSelectedSite(nextSite);
        if (nextSite) loadAlerts(nextSite.id);
      }
      if (user?.role === "owner" || user?.role === "admin") {
        loadAuditLogs();
      }
    } catch (err) {
      setError(err.message || "Failed to delete site");
    }
  }

  async function runScan(siteId) {
    setError("");
    setScanningSiteId(siteId);
    setScanResult(null);
    try {
      const result = await apiFetch(`/api/scan/${siteId}`, { method: "POST" });
      setScanResult(result);
      loadAlerts(siteId);
      if (user?.role === "owner" || user?.role === "admin") {
        loadAuditLogs();
      }
    } catch (err) {
      setError("Scan execution failed: " + err.message);
    } finally {
      setScanningSiteId(null);
    }
  }

  async function resolveAlert(alertId, siteId) {
    setError("");
    try {
      await apiFetch(`/api/alerts/${alertId}/resolve`, { method: "POST" });
      loadAlerts(siteId);
      if (user?.role === "owner" || user?.role === "admin") {
        loadAuditLogs();
      }
    } catch (err) {
      setError("Failed to resolve alert: " + err.message);
    }
  }

  function handleLogout() {
    setToken(null);
    router.push("/");
  }

  if (!user) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <svg className="spinner" style={{ width: "32px", height: "32px", color: "var(--primary)" }} fill="none" viewBox="0 0 24 24">
          <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    );
  }

  const isScanLoading = scanningSiteId !== null;
  const currentAlerts = selectedSite ? alerts[selectedSite.id] || [] : [];
  const activeAlerts = currentAlerts.filter(a => !a.resolved);
  const resolvedAlerts = currentAlerts.filter(a => a.resolved);

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <div className="header-row">
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "24px" }}>
            <span style={{ display: "inline-flex", padding: "6px", background: "rgba(139, 92, 246, 0.1)", borderRadius: "8px" }}>
              <svg style={{ width: "20px", height: "20px", color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </span>
            SYSTEM<span style={{ color: "var(--primary)" }}>SIEGE</span>
          </h1>
          <p style={{ fontSize: "11px", color: "var(--text-muted)", letterSpacing: "1px", textTransform: "uppercase", marginTop: "2px" }}>
            Security Operations Dashboard
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", fontWeight: "600" }}>{user.email}</div>
            <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end", marginTop: "3px" }}>
              <span className="badge badge-accent">{user.org_name}</span>
              <span className="badge badge-primary">Role: {user.role}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: "8px 16px", fontSize: "13px", borderRadius: "6px" }}>
            Logout
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: "rgba(239, 68, 68, 0.1)",
          border: "1px solid rgba(239, 68, 68, 0.2)",
          padding: "12px 16px",
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          color: "#fca5a5"
        }}>
          <svg style={{ width: "18px", height: "18px", color: "var(--danger)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span style={{ fontSize: "13.5px" }}>{error}</span>
        </div>
      )}

      {/* Main Panel Grid */}
      <div className="dashboard-grid">
        {/* Left Side Controls (Sites form & list) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

          {/* Add Site Card */}
          <div className="glass-panel animate-enter">
            <h3 style={{ fontSize: "16px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <svg style={{ width: "16px", height: "16px", color: "var(--accent)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Scan Target Setup
            </h3>
            {user.role === "viewer" ? (
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Your account possesses read-only viewer privileges. You cannot register new monitoring sites.
              </p>
            ) : (
              <form onSubmit={addSite} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <input
                  placeholder="Target Name (e.g. Prod Portal)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
                <input
                  placeholder="HTTPS Target URL"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  type="url"
                />
                <button type="submit" className="btn btn-secondary" disabled={submitting} style={{ width: "100%", padding: "10px" }}>
                  {submitting ? "Registering..." : "Add Monitoring Target"}
                </button>
              </form>
            )}
          </div>

          {/* Monitored targets card */}
          <div className="glass-panel animate-enter" style={{ flex: 1 }}>
            <h3 style={{ fontSize: "16px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <svg style={{ width: "16px", height: "16px", color: "var(--accent)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Monitoring Registry ({sites.length})
            </h3>
            {sites.length === 0 ? (
              <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-muted)" }}>
                <svg style={{ width: "24px", height: "24px", opacity: 0.5, marginBottom: "8px" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <div style={{ fontSize: "12px" }}>No monitored sites registered yet</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {sites.map((s) => {
                  const isActive = selectedSite?.id === s.id;
                  const siteAlerts = alerts[s.id] || [];
                  const activeAlertCount = siteAlerts.filter(a => !a.resolved).length;
                  return (
                    <div
                      key={s.id}
                      onClick={() => { setSelectedSite(s); loadAlerts(s.id); }}
                      style={{
                        padding: "14px",
                        borderRadius: "8px",
                        background: isActive ? "rgba(139, 92, 246, 0.08)" : "rgba(255, 255, 255, 0.01)",
                        border: isActive ? "1px solid rgba(139, 92, 246, 0.3)" : "1px solid rgba(255, 255, 255, 0.04)",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        position: "relative"
                      }}
                      className={isActive ? "scanning-card" : ""}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "4px" }}>
                        <span style={{ fontWeight: "600", fontSize: "14.5px", color: isActive ? "#fff" : "var(--text-dim)" }}>
                          {s.name}
                        </span>
                        <div style={{ display: "flex", gap: "6px" }}>
                          {activeAlertCount > 0 && (
                            <span className="badge badge-danger pulse-danger" style={{ animationDuration: "1.5s" }}>
                              {activeAlertCount} alert
                            </span>
                          )}
                          {(user.role === "admin" || user.role === "owner") && (
                            <button
                              onClick={(e) => deleteSite(s.id, e)}
                              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", opacity: 0.6 }}
                              title="Delete monitoring target"
                            >
                              <svg style={{ width: "14px", height: "14px" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {s.url}
                      </div>

                      {isActive && (
                        <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
                          <button
                            disabled={isScanLoading || user.role === "viewer"}
                            onClick={() => runScan(s.id)}
                            className="btn"
                            style={{ flex: 1, padding: "6px 12px", fontSize: "12px", borderRadius: "4px" }}
                          >
                            {scanningSiteId === s.id ? (
                              <>
                                <svg className="spinner" style={{ width: "12px", height: "12px", marginRight: "4px" }} fill="none" viewBox="0 0 24 24">
                                  <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                  <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Auditing...
                              </>
                            ) : (
                              "Scan Target"
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Side Assessment & Alerts Panels */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

          {/* Assessment Result Panel */}
          {selectedSite ? (
            <div className="glass-panel animate-enter">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                <div>
                  <h2 style={{ fontSize: "18px" }}>Vulnerability Assessment Report</h2>
                  <p style={{ fontSize: "12px", color: "var(--text-dim)" }}>
                    Target: <strong style={{ color: "#fff" }}>{selectedSite.name}</strong> ({selectedSite.url})
                  </p>
                </div>
                {scanningSiteId === selectedSite.id && (
                  <span className="badge badge-accent pulse-danger">Scanning Live</span>
                )}
              </div>

              {/* Scanning Active Placeholder */}
              {scanningSiteId === selectedSite.id ? (
                <div style={{ padding: "60px 20px", textAlign: "center" }}>
                  <div style={{ display: "inline-flex", marginBottom: "16px", position: "relative" }}>
                    <svg className="spinner" style={{ width: "48px", height: "48px", color: "var(--primary)" }} viewBox="0 0 24 24" fill="none">
                      <circle style={{ opacity: 0.15 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                      <path style={{ opacity: 0.8 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  </div>
                  <h4 style={{ marginBottom: "6px" }}>Analyzing HTTP Headers & Vulnerabilities</h4>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>Running SSL verification and testing for defacement indicators...</p>
                </div>
              ) : scanResult ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  {/* Score circle layout */}
                  <div style={{ display: "flex", alignItems: "center", gap: "20px", padding: "16px", background: "rgba(0, 0, 0, 0.2)", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.04)" }}>

                    <div style={{ position: "relative", width: "70px", height: "70px", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", background: scanResult.score >= 80 ? "rgba(16, 185, 129, 0.1)" : scanResult.score >= 60 ? "rgba(245, 158, 11, 0.1)" : "rgba(239, 68, 68, 0.1)", border: `3px solid ${scanResult.score >= 80 ? "var(--success)" : scanResult.score >= 60 ? "var(--warning)" : "var(--danger)"}` }}>
                      <span style={{ fontSize: "20px", fontWeight: "700", fontFamily: "var(--font-heading)" }}>{scanResult.score}</span>
                    </div>

                    <div>
                      <h4 style={{ fontSize: "15px" }}>Security Index Rating</h4>
                      <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                        {scanResult.score >= 80 ? (
                          <span style={{ color: "var(--success)" }}>Secure status. Optimal security configuration observed.</span>
                        ) : scanResult.score >= 60 ? (
                          <span style={{ color: "var(--warning)" }}>Warning status. Moderate vulnerabilities identified.</span>
                        ) : (
                          <span style={{ color: "var(--danger)", fontWeight: "500" }}>Critical danger. Dangerous vulnerabilities or missing protections.</span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* AI Summary Insights Card */}
                  {scanResult.ai_summary && (
                    <div style={{
                      padding: "16px",
                      borderRadius: "8px",
                      background: "rgba(139, 92, 246, 0.04)",
                      border: "1px solid rgba(139, 92, 246, 0.15)"
                    }}>
                      <h4 style={{ fontSize: "13px", color: "var(--primary)", textTransform: "uppercase", letterSpacing: "1px", display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                        <svg style={{ width: "14px", height: "14px" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        AI Security Advisory
                      </h4>
                      <div style={{ fontSize: "13px", color: "var(--text-dim)" }}>
                        {scanResult.ai_summary.advisor_text || scanResult.ai_summary.summary || JSON.stringify(scanResult.ai_summary)}
                      </div>
                    </div>
                  )}

                  {/* HTTP Header Checks */}
                  <div>
                    <h4 style={{ fontSize: "13px", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
                      HTTP Headers Integrity Checks
                    </h4>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {scanResult.scan.headers ? Object.entries(scanResult.scan.headers).map(([hdr, details]) => {
                        const isPresent = Boolean(details && details !== "Missing");
                        let statusColor = "var(--danger)";
                        let isOk = false;
                        if (isPresent) {
                          statusColor = "var(--success)";
                          isOk = true;
                        }
                        return (
                          <div key={hdr} style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                            padding: "10px 12px",
                            background: "rgba(0, 0, 0, 0.15)",
                            borderRadius: "6px",
                            border: `1px solid ${isPresent ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)"}`
                          }}>
                            <span style={{
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              width: "18px",
                              height: "18px",
                              borderRadius: "50%",
                              background: isOk ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                              color: statusColor
                            }}>
                              {isOk ? "✓" : "✗"}
                            </span>
                            <div style={{ fontSize: "12px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              <div style={{ fontWeight: "600", color: "#fff" }}>{hdr}</div>
                              <div style={{ color: isOk ? "var(--text-muted)" : "var(--danger)", fontSize: "10px" }}>
                                {isOk ? "Configured" : "Missing Header"}
                              </div>
                            </div>
                          </div>
                        );
                      }) : (
                        <p style={{ gridColumn: "span 2", fontSize: "12px", color: "var(--text-muted)" }}>No HTTP Header reports in this scan.</p>
                      )}
                    </div>
                  </div>

                  {/* Raw Audit Logs JSON */}
                  <div style={{ marginTop: "10px" }}>
                    <h4 style={{ fontSize: "13px", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
                      Raw Auditor Audit Payload
                    </h4>
                    <pre style={{ fontSize: "11px", maxHeight: "150px" }}>
                      {JSON.stringify(scanResult.scan, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-muted)" }}>
                  <svg style={{ width: "36px", height: "36px", opacity: 0.3, marginBottom: "12px" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h4 style={{ marginBottom: "4px" }}>Report Index Empty</h4>
                  <p style={{ fontSize: "12px" }}>Select scan target, then click "Scan Target" above to audit the site.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)" }}>
              <h4>No Site Selected</h4>
              <p style={{ fontSize: "12px", marginTop: "4px" }}>Add or select a monitoring target from the registry list.</p>
            </div>
          )}

          {/* Site-Specific Alerts Center */}
          {selectedSite && (
            <div className="glass-panel animate-enter">
              <h3 style={{ fontSize: "16px", marginBottom: "16px", display: "flex", justify: "space-between", align: "center" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <svg style={{ width: "16px", height: "16px", color: "var(--danger)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Alert Operations Center
                </span>
                {activeAlerts.length > 0 && (
                  <span className="badge badge-danger">{activeAlerts.length} Unresolved</span>
                )}
              </h3>

              {currentAlerts.length === 0 ? (
                <div style={{ textAlign: "center", padding: "20px 0", color: "var(--text-muted)", fontSize: "12px" }}>
                  ✓ Clean security status. No defacement or vulnerability flags raised.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {activeAlerts.map((a) => {
                    const isSL1 = a.severity === "SL-1";
                    return (
                      <div key={a.id} style={{
                        padding: "12px 14px",
                        borderRadius: "8px",
                        background: isSL1 ? "rgba(239, 68, 68, 0.05)" : "rgba(245, 158, 11, 0.05)",
                        border: `1px solid ${isSL1 ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)"}`,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: "10px"
                      }}>
                        <div>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <span className={`badge ${isSL1 ? "badge-danger" : "badge-warning"}`}>{a.severity}</span>
                            <span style={{ fontWeight: "600", fontSize: "13.5px" }}>{a.title}</span>
                          </div>
                          <p style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>
                            {a.description}
                          </p>
                          <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                            Generated {new Date(a.created_at).toLocaleString()}
                          </span>
                        </div>
                        {user.role === "viewer" ? null : (
                          <button
                            onClick={() => resolveAlert(a.id, selectedSite.id)}
                            className="btn btn-secondary"
                            style={{ padding: "6px 12px", fontSize: "11px", whiteSpace: "nowrap", flexShrink: 0, borderRadius: "4px", borderColor: "rgba(255, 255, 255, 0.15)" }}
                          >
                            Resolve Alert
                          </button>
                        )}
                      </div>
                    );
                  })}
                  {activeAlerts.length === 0 && (
                    <div style={{ fontSize: "12px", color: "var(--success)", padding: "10px", textAlign: "center" }}>
                      All security flags resolved.
                    </div>
                  )}

                  {resolvedAlerts.length > 0 && (
                    <div style={{ marginTop: "12px", borderTop: "1px solid var(--panel-border)", paddingTop: "12px" }}>
                      <h4 style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
                        Resolved Timeline ({resolvedAlerts.length})
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", opacity: 0.6 }}>
                        {resolvedAlerts.map((ra) => (
                          <div key={ra.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", background: "rgba(255,255,255, 0.02)", padding: "6px 10px", borderRadius: "4px" }}>
                            <span>{ra.title}</span>
                            <span style={{ color: "var(--success)" }}>RESOLVED</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Admin Audit Trail Timeline */}
      {(user.role === "owner" || user.role === "admin") && auditLogs.length > 0 && (
        <div className="glass-panel animate-enter" style={{ marginTop: "8px" }}>
          <h3 style={{ fontSize: "16px", marginBottom: "16px", display: "flex", justify: "space-between", alignItems: "center" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <svg style={{ width: "16px", height: "16px", color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Enterprise Audit Log & Event Log History (Owner/Admin)
            </span>
            <button onClick={loadAuditLogs} style={{ background: "none", border: "none", color: "var(--accent)", fontSize: "12px", cursor: "pointer" }}>
              Refresh Logs
            </button>
          </h3>

          <div style={{ maxHeight: "250px", overflowY: "auto", paddingRight: "8px" }}>
            <table style={{ minWidth: "100%" }}>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Details</th>
                  <th>User ID</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((l) => (
                  <tr key={l.id}>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {new Date(l.created_at).toLocaleString()}
                    </td>
                    <td>
                      <span className="badge badge-accent" style={{ fontSize: "10px" }}>{l.action}</span>
                    </td>
                    <td style={{ color: "#fff", fontSize: "12.5px" }}>{l.resource}</td>
                    <td style={{ fontSize: "12px", color: "var(--text-dim)" }}>
                      {l.details ? JSON.stringify(l.details) : ""}
                    </td>
                    <td style={{ fontSize: "11px", color: "var(--text-muted)" }}>{l.user_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
