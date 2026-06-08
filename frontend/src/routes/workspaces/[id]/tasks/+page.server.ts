import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import * as tasks from '$lib/api/tasks';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad } from './$types';

// Tasks for a workspace. Confirms the workspace belongs to the caller (via the
// list, same as the detail page — no single-workspace GET), then fetches its
// tasks. A workspace the user isn't in -> notFound (non-disclosure).
export const load: PageServerLoad = async (event) => {
	const user = requireAuth(event);
	const accessToken = event.cookies.get(cookieNames.access);

	if (!accessToken) {
		return { user, workspace: null, tasks: [], loadError: true, notFound: false };
	}

	try {
		const list = await workspaces.list(accessToken);
		const workspace = list.find((w) => w.id === event.params.id) ?? null;

		if (!workspace) {
			return { user, workspace: null, tasks: [], loadError: false, notFound: true };
		}

		const taskList = await tasks.list(accessToken, workspace.id);
		return { user, workspace, tasks: taskList, loadError: false, notFound: false };
	} catch (cause) {
		if (!(cause instanceof ApiError)) {
			console.error('tasks load: unexpected error', cause);
		}
		return { user, workspace: null, tasks: [], loadError: true, notFound: false };
	}
};
