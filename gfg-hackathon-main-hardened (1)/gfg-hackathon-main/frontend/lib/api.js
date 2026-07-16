const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function getToken() {
  if (typeof window === "undefined") return null;
  return window.__ACCESS_TOKEN__ || null; // kept in-memory only, not localStorage, to reduce XSS token theft risk
}

export function setToken(token) {
  if (typeof window !== "undefined") window.__ACCESS_TOKEN__ = token;
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function login(email, password) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function signup(orgName, email, password) {
  return apiFetch("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ org_name: orgName, email, password }),
  }).then((data) => {
    setToken(data.access_token);
    return data;
  });
}
