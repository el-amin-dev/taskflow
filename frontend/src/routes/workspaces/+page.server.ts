import { fail } from '@sveltejs/kit';
import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad, Actions } from './$types';

// Protected: requireAuth redirects to /login if there's no session.
// Then fetch the caller's workspaces with the access token from the cookie
// (read fresh — hooks may have just refreshed it).
export const load: PageServerLoad = async (event) => {
	const user = requireAuth(event);
	const accessToken = event.cookies.get(cookieNames.access);

	if (!accessToken) {
		return { user, workspaces: [], loadError: true };
	}

	try {
		const list = await workspaces.list(accessToken);
		return { user, workspaces: list, loadError: false };
	} catch (cause) {
		if (!(cause instanceof ApiError)) {
			console.error('workspaces load: unexpected error', cause);
		}
		return { user, workspaces: [], loadError: true };
	}
};

export const actions: Actions = {
	// Create a workspace. Guarded like the load; reads the name from the form,
	// the token from the cookie, and delegates to the typed client.
	default: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { error: 'Your session expired. Please log in again.', name: '' });
		}

		const data = await event.request.formData();
		const name = String(data.get('name') ?? '').trim();

		if (!name) {
			return fail(400, { error: 'Workspace name is required.', name });
		}

		try {
			await workspaces.create(accessToken, { name });
			return { success: true };
		} catch (cause) {
			// Keep the typed name so the form can repopulate. Branch on code if
			// the backend ever returns a specific one; generic message for now.
			if (!(cause instanceof ApiError)) {
				console.error('workspace create: unexpected error', cause);
			}
			return fail(400, { error: 'Could not create the workspace. Please try again.', name });
		}
	}
};
