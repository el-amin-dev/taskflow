import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Already logged in? No reason to see the register form — send home.
export const load: PageServerLoad = ({ locals }) => {
	if (locals.user) {
		throw redirect(303, '/');
	}
	return {};
};
