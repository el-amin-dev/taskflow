import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Logged-in users get their workspaces, not the marketing landing page.
// Anonymous visitors fall through and see the landing page.
export const load: PageServerLoad = ({ locals }) => {
	if (locals.user) {
		throw redirect(303, '/workspaces');
	}
	return {};
};

