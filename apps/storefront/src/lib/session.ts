const SESSION_KEY = "visual-shop:session-token";

export function getSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SESSION_KEY, token);
}

export function sessionHeaders(): HeadersInit {
  const token = getSessionToken();
  return token ? { "X-Session-Token": token } : {};
}

export function captureSessionToken(response: Response): void {
  const token = response.headers.get("X-Session-Token");
  if (token) setSessionToken(token);
}
