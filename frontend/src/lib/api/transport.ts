import { ApiError } from './errors';

// Resolve and validate config at module-load time (fail-fast, 12-factor §III).
// A missing or empty VITE_API_URL crashes here, not on the first request.
const baseUrl = import.meta.env.VITE_API_URL;
if (typeof baseUrl !== 'string' || baseUrl.length === 0) {
	throw new Error('VITE_API_URL is not set. Configure it in frontend/.env');
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

type RequestOptions = {
	method?: Method;
	body?: unknown;
	headers?: Record<string, string>;
	signal?: AbortSignal;
};

// Single point of HTTP transport. Callers (endpoint modules) parameterize T
// to the generated response type. Returns parsed JSON on 2xx, throws ApiError
// on any non-2xx (envelope unwrapped) or network failure.
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const { method = 'GET', body, headers = {}, signal } = options;

	const init: RequestInit = {
		method,
		headers: {
			Accept: 'application/json',
			...(body !== undefined && { 'Content-Type': 'application/json' }),
			...headers
		},
		signal
	};

	if (body !== undefined) {
		init.body = JSON.stringify(body);
	}

	let response: Response;
	try {
		response = await fetch(`${baseUrl}${path}`, init);
	} catch (cause) {
		throw ApiError.fromNetwork(cause);
	}

	if (!response.ok) {
		throw await ApiError.fromResponse(response);
	}

	// 204 No Content (e.g. /logout, DELETEs) — no body to parse.
	if (response.status === 204) {
		return undefined as T;
	}

	return (await response.json()) as T;
}
