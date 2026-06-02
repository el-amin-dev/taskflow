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

// POST /api/auth/register
// Browser sends { email, password }. We create the account on the backend,
// then immediately log in to issue tokens, then set httpOnly cookies and
// return the user. Browser JS never sees a token.
export const POST: RequestHandler = async ({ request, cookies }) => {
	const body = await request.json();

	try {
		const user = await auth.register(body);
		const tokens = await auth.login({ email: body.email, password: body.password });

		cookies.set('taskflow_access', tokens.access_token, {
			...COOKIE_OPTS,
			maxAge: ACCESS_TTL_SECONDS
		});
		cookies.set('taskflow_refresh', tokens.refresh_token, {
			...COOKIE_OPTS,
			maxAge: REFRESH_TTL_SECONDS
		});

		return json(user, { status: 201 });
	} catch (cause) {
		if (cause instanceof ApiError) {
			// Surface the backend's machine-readable code so the form can branch on it.
			return json({ code: cause.code, message: cause.message }, { status: cause.status });
		}
		throw error(500, 'Unexpected error');
	}
};
