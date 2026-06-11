import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import * as tasks from '$lib/api/tasks';
import * as comments from '$lib/api/comments';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad, Actions } from './$types';
import { fail } from '@sveltejs/kit';


// Task detail + comments. No single-workspace or single-task GET exists, so we
// resolve both by listing and filtering (workspace -> its tasks -> the task),
// then fetch the task's comments page. notFound at any missing level (a task
// the caller can't see "doesn't exist" — non-disclosure).
export const load: PageServerLoad = async (event) => {
	const user = requireAuth(event);
	const accessToken = event.cookies.get(cookieNames.access);

	if (!accessToken) {
		return { user, workspace: null, task: null, comments: [], loadError: true, notFound: false };
	}

	try {
		const wsList = await workspaces.list(accessToken);
		const workspace = wsList.find((w) => w.id === event.params.id) ?? null;
		if (!workspace) {
			return { user, workspace: null, task: null, comments: [], loadError: false, notFound: true };
		}

		const taskList = await tasks.list(accessToken, workspace.id);
		const task = taskList.find((t) => t.id === event.params.taskId) ?? null;
		if (!task) {
			return { user, workspace, task: null, comments: [], loadError: false, notFound: true };
		}

		const page = await comments.list(accessToken, workspace.id, task.id);
		return { user, workspace, task, comments: page.items, loadError: false, notFound: false };
	} catch (cause) {
		if (!(cause instanceof ApiError)) {
			console.error('task detail load: unexpected error', cause);
		}
		return { user, workspace: null, task: null, comments: [], loadError: true, notFound: false };
	}
};

export const actions: Actions = {
	// Add a comment to this task. body required.
	addComment: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { commentError: 'Your session expired. Please log in again.', body: '' });
		}

		const data = await event.request.formData();
		const body = String(data.get('body') ?? '').trim();

		if (!body) {
			return fail(400, { commentError: 'Comment cannot be empty.', body });
		}

		try {
			await comments.create(accessToken, event.params.id, event.params.taskId, { body });
			return { commentAdded: true };
		} catch (cause) {
			if (!(cause instanceof ApiError)) {
				console.error('add comment: unexpected error', cause);
			}
			return fail(400, { commentError: 'Could not add the comment. Please try again.', body });
		}
	},
		updateTask: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { editError: 'Your session expired. Please log in again.' });
		}

		const data = await event.request.formData();
		const title = String(data.get('title') ?? '').trim();
		const description = String(data.get('description') ?? '').trim();

		if (!title) {
			return fail(400, { editError: 'Title is required.', editTitle: title, editDescription: description });
		}

		try {
			await tasks.update(accessToken, event.params.id, event.params.taskId, {
				title,
				description: description || null
			});
			return { taskUpdated: true };
		} catch (cause) {
			if (!(cause instanceof ApiError)) {
				console.error('update task: unexpected error', cause);
			}
			return fail(400, { editError: 'Could not update the task. Please try again.', editTitle: title, editDescription: description });
		}
	}
};
