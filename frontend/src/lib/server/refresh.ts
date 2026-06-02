import * as auth from '$lib/api/auth';
import type { components } from '$lib/api/types';

type TokenResponse = components['schemas']['TokenResponse'];

// Single-flight refresh: concurrent calls with the SAME refresh-token value
// share one in-flight /refresh request, instead of each firing their own.
//
// Why: the backend's refresh tokens are single-use with theft detection
// (SECURITY.md). Two requests refreshing the same token would make the second
// replay an already-spent token, which the backend treats as theft and
// responds to by killing the whole token family — logging the user out for
// no reason ("it randomly logs me out"). Sharing one in-flight promise
// prevents the replay.
//
// BOUNDARY: this Map lives in one Node process. With multiple SvelteKit
// replicas (Phase C / k8s) each process has its own Map and the race returns
// across replicas — the real fix at that scale is a shared lock (Redis) or
// sticky sessions. Tracked; sufficient for single-process Phase A/B.
const inFlight = new Map<string, Promise<TokenResponse>>();

export function refreshTokens(refreshToken: string): Promise<TokenResponse> {
	const existing = inFlight.get(refreshToken);
	if (existing) return existing;

	const promise = auth
		.refresh({ refresh_token: refreshToken })
		.finally(() => {
			// Whether it succeeded or failed, this token value is done —
			// drop it so a later (legitimately new) token can refresh.
			inFlight.delete(refreshToken);
		});

	inFlight.set(refreshToken, promise);
	return promise;
}
