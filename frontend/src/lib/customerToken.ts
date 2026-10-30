const STORAGE_KEY = "scopebridge.portal.token";

export function rememberPortalToken(token: string): void {
  window.sessionStorage.setItem(STORAGE_KEY, token);
}

export function readPortalToken(): string | null {
  return window.sessionStorage.getItem(STORAGE_KEY);
}

export function forgetPortalToken(): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
}
