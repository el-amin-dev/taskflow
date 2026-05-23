import { request } from '$lib/api/transport';
import { ApiError } from '$lib/api/errors';
import type { PageServerLoad } from './$types';

type HealthResponse = { status: string; uptime_seconds: number };

// Operator-facing health probe. Calls the backend's /health from the server
// runtime, surfaces success or error to the page. Useful in deployed
// environments (Phase C) to confirm frontend-to-backend wiring without
// shelling into a pod.
export const load: PageServerLoad = async () => {
	try {
		const health = await request<HealthResponse>('/health');
		return { ok: true as const, health };
	} catch (cause) {
		if (cause instanceof ApiError) {
			return { ok: false as const, code: cause.code, message: cause.message, status: cause.status };
		}
		throw cause;
	}
};
