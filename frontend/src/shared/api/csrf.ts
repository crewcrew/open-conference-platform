// CSRF token lives in memory only — never in localStorage, sessionStorage or cookies we set.
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null | undefined) {
  csrfToken = token || null;
}

export function getCsrfToken(): string | null {
  return csrfToken;
}

