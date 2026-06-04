import { redirect } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';
import type { components } from '$lib/api/types';

type UserResponse = components['schemas']['UserResponse'];

// Guard for protected routes. Call from a +page.server.ts / +layout.server.ts
// load: returns the authenticated user (narrowed to non-null) or redirects to
// /login. Deny-by-default — a route using this cannot render for an anonymous
// visitor (OWASP A01).
//
// locals.user is populated by hooks.server.ts (which also handles silent
// refresh), so an expired-but-refreshable session is already recovered by the
// time this runs.
//
// NOTE: redirects to a plain /login. Capturing the attempted URL for
// post-login bounce-back (?redirectTo=) is a deferred enhancement — add it
// when multiple protected routes make it worthwhile.
export function requireAuth(event: RequestEvent): UserResponse {
	if (!event.locals.user) {
		throw redirect(303, '/login');
	}
	return event.locals.user;
}
