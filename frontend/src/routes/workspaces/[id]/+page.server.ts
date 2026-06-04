import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad } from './$types';

// Protected workspace detail. No single-workspace GET exists on the backend,
// so we fetch the caller's list and find the match by id. Fine at this scale;
// a dedicated GET /v1/workspaces/{id} would be the optimization if lists grow.
//
// A workspace the user doesn't belong to won't be in the list -> notFound,
// which is also the right non-disclosure behavior (cross-tenant = "doesn't
// exist"), mirroring the backend.
export const load: PageServerLoad = async (event) => {
	const user = requireAuth(event);
	const accessToken = event.cookies.get(cookieNames.access);

	if (!accessToken) {
		return { user, workspace: null, loadError: true, notFound: false };
	}

	try {
		const list = await workspaces.list(accessToken);
		const workspace = list.find((w) => w.id === event.params.id) ?? null;
		return { user, workspace, loadError: false, notFound: workspace === null };
	} catch (cause) {
		if (!(cause instanceof ApiError)) {
			console.error('workspace detail load: unexpected error', cause);
		}
		return { user, workspace: null, loadError: true, notFound: false };
	}
};
