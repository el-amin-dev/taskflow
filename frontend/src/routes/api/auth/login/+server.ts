import { json, error } from '@sveltejs/kit';
import * as auth from '$lib/api/auth';
import { ApiError } from '$lib/api/errors';
import { setAuthCookies } from '$lib/server/cookies';
import type { RequestHandler } from './$types';

// POST /api/auth/login
// Exchange credentials for a token pair, set httpOnly cookies, return the
// user (fetched via /me, since login itself returns only tokens).
export const POST: RequestHandler = async ({ request, cookies }) => {
	const body = await request.json();

	try {
		const tokens = await auth.login(body);
		setAuthCookies(cookies, tokens);
		const user = await auth.me(tokens.access_token);
		return json(user, { status: 200 });
	} catch (cause) {
		if (cause instanceof ApiError) {
			return json({ code: cause.code, message: cause.message }, { status: cause.status });
		}
		throw error(500, 'Unexpected error');
	}
};

