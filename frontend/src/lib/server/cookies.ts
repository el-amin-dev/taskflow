import type { Cookies } from '@sveltejs/kit';
import type { components } from '$lib/api/types';

// Parse a required positive-integer TTL from env. Fail-fast (12-factor §III):
// a missing or non-numeric value crashes at module load, not on first request.
function parseTtl(raw: unknown, name: string): number {
	const n = Number(raw);
	if (!Number.isInteger(n) || n <= 0) {
		throw new Error(`${name} must be a positive integer (seconds). Got: ${String(raw)}`);
	}
	return n;
}

type TokenResponse = components['schemas']['TokenResponse'];

const ACCESS_COOKIE = 'taskflow_access';
const REFRESH_COOKIE = 'taskflow_refresh';

const ACCESS_TTL_SECONDS = parseTtl(import.meta.env.VITE_ACCESS_TTL_SECONDS, 'VITE_ACCESS_TTL_SECONDS');
const REFRESH_TTL_SECONDS = parseTtl(import.meta.env.VITE_REFRESH_TTL_SECONDS, 'VITE_REFRESH_TTL_SECONDS');

const COOKIE_OPTS = {
	httpOnly: true,
	sameSite: 'lax' as const,
	path: '/',
	secure: process.env.NODE_ENV === 'production'
};

// Write the access + refresh tokens as httpOnly cookies. Called by every
// server route that issues a session (register, login, refresh). One place
// owns cookie names, TTLs, and security attributes.
export function setAuthCookies(cookies: Cookies, tokens: TokenResponse): void {
	cookies.set(ACCESS_COOKIE, tokens.access_token, { ...COOKIE_OPTS, maxAge: ACCESS_TTL_SECONDS });
	cookies.set(REFRESH_COOKIE, tokens.refresh_token, { ...COOKIE_OPTS, maxAge: REFRESH_TTL_SECONDS });
}

// Clear both cookies — called on logout and on failed refresh.
export function clearAuthCookies(cookies: Cookies): void {
		cookies.delete(ACCESS_COOKIE, COOKIE_OPTS);
	cookies.delete(REFRESH_COOKIE, COOKIE_OPTS);
}

// Cookie-name accessors — so reading code (hooks.server.ts) doesn't hardcode
// the strings.
export const cookieNames = { access: ACCESS_COOKIE, refresh: REFRESH_COOKIE } as const;
