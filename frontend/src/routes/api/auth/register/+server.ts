import { json, error } from '@sveltejs/kit';
import * as auth from '$lib/api/auth';
import { ApiError } from '$lib/api/errors';
import { setAuthCookies } from '$lib/server/cookies';
import type { RequestHandler } from './$types';

// POST /api/auth/register
// Create the account, immediately log in to issue tokens, set httpOnly
// cookies, return the user. Browser JS never sees a token.
export const POST: RequestHandler = async ({ request, cookies }) => {
	const body = await request.json();

	try {
		const user = await auth.register(body);
		const tokens = await auth.login({ email: body.email, password: body.password });
		setAuthCookies(cookies, tokens);
		return json(user, { status: 201 });
	} catch (cause) {
		if (cause instanceof ApiError) {
			return json({ code: cause.code, message: cause.message }, { status: cause.status });
		}
		throw error(500, 'Unexpected error');
	}
};
