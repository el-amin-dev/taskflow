import type { LayoutServerLoad } from './$types';

// Surface the authenticated user (resolved in hooks) to the layout, so the
// header can reflect login state. Returns null when logged out.
export const load: LayoutServerLoad = ({ locals }) => {
	return { user: locals.user };
};
