import { fail } from '@sveltejs/kit';
import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import * as tasks from '$lib/api/tasks';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad, Actions } from './$types';

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

const VALID_STATUSES = ['todo', 'in_progress', 'done'] as const;

export const actions: Actions = {
	create: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { error: 'Your session expired. Please log in again.', title: '', description: '', status: 'todo' });
		}

		const data = await event.request.formData();
		const title = String(data.get('title') ?? '').trim();
		const description = String(data.get('description') ?? '').trim();
		const status = String(data.get('status') ?? 'todo');

		if (!title) {
			return fail(400, { error: 'Title is required.', title, description, status });
		}
		if (!VALID_STATUSES.includes(status as (typeof VALID_STATUSES)[number])) {
			return fail(400, { error: 'Pick a valid status.', title, description, status });
		}

		try {
			await tasks.create(accessToken, event.params.id, {
				title,
				description: description || null,
				status: status as (typeof VALID_STATUSES)[number]
			});
			return { created: true };
		} catch (cause) {
			if (!(cause instanceof ApiError)) {
				console.error('task create: unexpected error', cause);
			}
			return fail(400, { error: 'Could not create the task. Please try again.', title, description, status });
		}
	},

	updateStatus: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { statusError: 'Your session expired. Please log in again.' });
		}

		const data = await event.request.formData();
		const taskId = String(data.get('task_id') ?? '');
		const status = String(data.get('status') ?? '');

		if (!taskId || !VALID_STATUSES.includes(status as (typeof VALID_STATUSES)[number])) {
			return fail(400, { statusError: 'Invalid status update.' });
		}

		try {
			await tasks.update(accessToken, event.params.id, taskId, {
				status: status as (typeof VALID_STATUSES)[number]
			});
			return { statusUpdated: true };
		} catch (cause) {
			if (!(cause instanceof ApiError)) {
				console.error('task status update: unexpected error', cause);
			}
			return fail(400, { statusError: 'Could not update the status.' });
		}
	}
};
