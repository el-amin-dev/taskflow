import type { Cookies } from '@sveltejs/kit';
import type { components } from '$lib/api/types';

type TokenResponse = components['schemas']['TokenResponse'];

const ACCESS_COOKIE = 'taskflow_access';
const REFRESH_COOKIE = 'taskflow_refresh';

const ACCESS_TTL_SECONDS = 60 * 15; // 15 min — matches backend JWT_ACCESS_TTL_MINUTES
const REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days — matches JWT_REFRESH_TTL_DAYS

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
	cookies.delete(ACCESS_COOKIE, { path: '/' });
	cookies.delete(REFRESH_COOKIE, { path: '/' });
}

// Cookie-name accessors — so reading code (hooks.server.ts) doesn't hardcode
// the strings.
export const cookieNames = { access: ACCESS_COOKIE, refresh: REFRESH_COOKIE } as const;
