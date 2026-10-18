/**
 * Tiny event bus between the API layer and the auth context.
 *
 * When an authenticated request comes back 401 (expired or invalid token), the
 * API layer calls `notifyUnauthorized()`; the AuthProvider listens, clears the
 * session and the protected layout redirects to /signin.
 */

const EVENT = "hsk:unauthorized";

export function notifyUnauthorized(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

export function onUnauthorized(handler: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}

/** The browser's IANA time zone (e.g. "Europe/Paris"), sent so days follow the user's clock. */
export function browserTimeZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}
