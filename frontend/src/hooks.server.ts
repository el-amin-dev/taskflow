import * as auth from '$lib/api/auth';
import { ApiError } from '$lib/api/errors';
import { cookieNames } from '$lib/server/cookies';
import type { Handle } from '@sveltejs/kit';

// Runs on every server request before routes/load. Reads the access cookie,
// validates it against the backend, and attaches the user (or null) to
// event.locals so all downstream code has one source of truth for auth state.
//
// NOTE: validates via /me (a backend round-trip per request). Fine for now;
// local JWT signature verification is a future optimization. Tracked.
// NOTE: silent refresh-on-expiry is added in a later commit; for now an
// expired access token simply yields user=null.
export const handle: Handle = async ({ event, resolve }) => {
	const accessToken = event.cookies.get(cookieNames.access);

	if (accessToken) {
		try {
			event.locals.user = await auth.me(accessToken);
		} catch (cause) {
			if (!(cause instanceof ApiError)) {
				console.error('hooks: unexpected error validating session', cause);
			}
			event.locals.user = null;
		}
	} else {
		event.locals.user = null;
	}

	return resolve(event);
};
