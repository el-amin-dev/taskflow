import { json, error } from '@sveltejs/kit';
import * as auth from '$lib/api/auth';
import { ApiError } from '$lib/api/errors';
import type { RequestHandler } from './$types';

const ACCESS_TTL_SECONDS = 60 * 15; // 15 min — matches backend JWT_ACCESS_TTL_MINUTES
const REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days — matches JWT_REFRESH_TTL_DAYS
const COOKIE_OPTS = {
	httpOnly: true,
	sameSite: 'lax' as const,
	path: '/',
	secure: process.env.NODE_ENV === 'production'
};

// POST /api/auth/login
// Exchange credentials for a token pair, set httpOnly cookies, return the user.
// We fetch /me after login so the browser gets the user object (login itself
// only returns tokens) — matches the register route's response shape.
export const POST: RequestHandler = async ({ request, cookies }) => {
	const body = await request.json();

	try {
		const tokens = await auth.login(body);

		cookies.set('taskflow_access', tokens.access_token, {
			...COOKIE_OPTS,
			maxAge: ACCESS_TTL_SECONDS
		});
		cookies.set('taskflow_refresh', tokens.refresh_token, {
			...COOKIE_OPTS,
			maxAge: REFRESH_TTL_SECONDS
		});

		const user = await auth.me(tokens.access_token);
		return json(user, { status: 200 });
	} catch (cause) {
		if (cause instanceof ApiError) {
			return json({ code: cause.code, message: cause.message }, { status: cause.status });
		}
		throw error(500, 'Unexpected error');
	}
};
