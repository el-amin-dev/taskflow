import { json } from '@sveltejs/kit';
import * as auth from '$lib/api/auth';
import { clearAuthCookies, cookieNames } from '$lib/server/cookies';
import type { RequestHandler } from './$types';

// POST /api/auth/logout
// Revoke the refresh token backend-side (best-effort) and clear both cookies.
// Idempotent and never errors — logout always "succeeds" from the user's view.
export const POST: RequestHandler = async ({ cookies }) => {
	const refreshToken = cookies.get(cookieNames.refresh);

	if (refreshToken) {
		try {
			await auth.logout({ refresh_token: refreshToken });
		} catch {
			// Backend revocation failed (already revoked, network, etc.).
			// Irrelevant to the user — we still clear local cookies below.
		}
	}

	clearAuthCookies(cookies);
	return json({ ok: true });
};
