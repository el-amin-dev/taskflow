import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad } from './$types';

// Protected: requireAuth redirects to /login if there's no session.
// Then fetch the caller's workspaces with the access token from the cookie
// (read fresh — hooks may have just refreshed it).
export const load: PageServerLoad = async (event) => {
	const user = requireAuth(event);
	const accessToken = event.cookies.get(cookieNames.access);

	// Guard guarantees a user, and a user implies a valid access cookie.
	// But narrow defensively for the type checker.
	if (!accessToken) {
		return { user, workspaces: [], loadError: true };
	}

	try {
		const list = await workspaces.list(accessToken);
		return { user, workspaces: list, loadError: false };
	} catch (cause) {
		// Transient/backend error — a genuinely invalid token would have been
		// caught by hooks (locals.user null -> guard redirect). Show a soft
		// error rather than crashing the page.
		if (!(cause instanceof ApiError)) {
			console.error('workspaces load: unexpected error', cause);
		}
		return { user, workspaces: [], loadError: true };
	}
};
