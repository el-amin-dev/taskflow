import { fail } from '@sveltejs/kit';
import { requireAuth } from '$lib/server/guards';
import { cookieNames } from '$lib/server/cookies';
import * as workspaces from '$lib/api/workspaces';
import * as members from '$lib/api/members';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad, Actions } from './$types';

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

const VALID_ROLES = ['admin', 'member', 'viewer'] as const;

export const actions: Actions = {
	// Invite a member by email + role. Admin-only on the backend; a non-admin
	// caller gets a 403 surfaced as a generic error.
	invite: async (event) => {
		requireAuth(event);
		const accessToken = event.cookies.get(cookieNames.access);
		if (!accessToken) {
			return fail(401, { error: 'Your session expired. Please log in again.' });
		}

		const data = await event.request.formData();
		const email = String(data.get('email') ?? '').trim();
		const role = String(data.get('role') ?? '');

		if (!email) {
			return fail(400, { error: 'Email is required.', email, role });
		}
		if (!VALID_ROLES.includes(role as (typeof VALID_ROLES)[number])) {
			return fail(400, { error: 'Pick a valid role.', email, role });
		}

		try {
			await members.invite(accessToken, event.params.id, {
				email,
				role: role as (typeof VALID_ROLES)[number]
			});
			return { invited: true, email, role };
		} catch (cause) {
			let error = 'Could not send the invite. Please try again.';
			if (cause instanceof ApiError) {
				if (cause.code === 'already_member') error = 'That person is already a member.';
				else if (cause.code === 'user_not_found') error = 'No account exists with that email.';
			} else {
				console.error('member invite: unexpected error', cause);
			}
			return fail(400, { error, email, role });
		}
	}
};
