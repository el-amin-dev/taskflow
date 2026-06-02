import * as auth from '$lib/api/auth';
import { ApiError } from '$lib/api/errors';
import { setAuthCookies, clearAuthCookies, cookieNames } from '$lib/server/cookies';
import { refreshTokens } from '$lib/server/refresh';
import type { Cookies, Handle } from '@sveltejs/kit';
import type { components } from '$lib/api/types';

type UserResponse = components['schemas']['UserResponse'];

// Attempt a silent refresh: exchange the refresh cookie for a new token pair,
// write the new cookies, return the user. Returns null if there's no refresh
// token or the refresh fails (expired, or theft-kill) — caller treats that as
// logged out.
async function tryRefresh(cookies: Cookies): Promise<UserResponse | null> {
	const refreshToken = cookies.get(cookieNames.refresh);
	if (!refreshToken) return null;

	try {
		const tokens = await refreshTokens(refreshToken);
		setAuthCookies(cookies, tokens);
		return await auth.me(tokens.access_token);
	} catch {
		// Refresh failed: dead/spent refresh token. Clear cookies; logged out.
		clearAuthCookies(cookies);
		return null;
	}
}

// Runs on every server request. Resolves auth state into event.locals.user:
//   valid access token        -> user
//   expired/invalid access    -> attempt silent refresh -> user or null
//   no access, refresh exists  -> attempt refresh -> user or null
//   nothing                    -> null
export const handle: Handle = async ({ event, resolve }) => {
	const accessToken = event.cookies.get(cookieNames.access);

	if (accessToken) {
		try {
			event.locals.user = await auth.me(accessToken);
		} catch (cause) {
			// Access token rejected. If it's an auth failure, try to refresh;
			// any other error also falls through to a refresh attempt, which
			// will cleanly yield null if it can't recover.
			if (cause instanceof ApiError) {
				event.locals.user = await tryRefresh(event.cookies);
			} else {
				console.error('hooks: unexpected error validating session', cause);
				event.locals.user = await tryRefresh(event.cookies);
			}
		}
	} else {
		// No access token — but a refresh token may still be valid (access
		// expired and was cleared, refresh still good).
		event.locals.user = await tryRefresh(event.cookies);
	}

	return resolve(event);
};
