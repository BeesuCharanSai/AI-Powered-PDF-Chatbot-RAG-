const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL || 'http://localhost:2024';
const TOKEN_KEY = 'auth_token';

/** Reads the stored session token, if any. */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseJsonOrThrow(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    // no JSON body
  }

  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(', ')
      : detail || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return body;
}

/** Creates a new account and stores the returned session token. */
export async function signup({ name, email, password }) {
  const response = await fetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  const data = await parseJsonOrThrow(response);
  setToken(data.token);
  return data.user;
}

/** Logs in with an existing account and stores the returned session token. */
export async function login({ email, password }) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await parseJsonOrThrow(response);
  setToken(data.token);
  return data.user;
}

/** Fetches the current user for the stored session token, if any/valid. */
export async function fetchCurrentUser() {
  const token = getToken();
  if (!token) return null;

  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    clearToken();
    return null;
  }

  const data = await response.json();
  return data.user;
}

export function logout() {
  clearToken();
}
