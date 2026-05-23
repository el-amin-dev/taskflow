export type ErrorCode =
	| 'email_unavailable'
	| 'invalid_credentials'
	| 'invalid_token'
	| 'user_not_found'
	| 'member_not_found'
	| 'already_member'
	| 'cannot_remove_owner'
	| 'task_not_found'
	| 'comment_not_found'
	| 'not_comment_author'
	| 'invalid_cursor'
	| 'invalid_request' // synthetic — Pydantic 422, see fromResponse()
	| 'network_error'; // synthetic — fetch threw before we got a Response

export class ApiError extends Error {
	readonly code: ErrorCode;
	readonly status: number;

	constructor(code: ErrorCode, message: string, status: number) {
		super(message);
		this.name = 'ApiError';
		this.code = code;
		this.status = status;
	}

	static async fromResponse(response: Response): Promise<ApiError> {
		const status = response.status;
		let body: unknown;
		try {
			body = await response.json();
		} catch {
			return new ApiError('invalid_request', `HTTP ${status}`, status);
		}

		if (status === 422 && isValidationBody(body)) {
			const first = body.detail[0];
			const where = first?.loc?.join('.') ?? 'request';
			const what = first?.msg ?? 'invalid';
			return new ApiError('invalid_request', `${where}: ${what}`, status);
		}

		if (isEnvelopeBody(body)) {
			return new ApiError(body.detail.code, body.detail.detail, status);
		}

		return new ApiError('invalid_request', `HTTP ${status}`, status);
	}

	// Build an ApiError when fetch itself failed (network down, CORS, abort).
	static fromNetwork(cause: unknown): ApiError {
		const message = cause instanceof Error ? cause.message : 'network error';
		return new ApiError('network_error', message, 0);
	}
}

// Narrow `unknown` to FastAPI's 422 shape.
function isValidationBody(b: unknown): b is { detail: Array<{ loc?: string[]; msg?: string }> } {
	return (
		typeof b === 'object' &&
		b !== null &&
		'detail' in b &&
		Array.isArray((b as { detail: unknown }).detail)
	);
}

// Narrow `unknown` to the unified envelope shape.
function isEnvelopeBody(b: unknown): b is { detail: { detail: string; code: ErrorCode } } {
	if (typeof b !== 'object' || b === null || !('detail' in b)) return false;
	const inner = (b as { detail: unknown }).detail;
	return (
		typeof inner === 'object' &&
		inner !== null &&
		'code' in inner &&
		'detail' in inner &&
		typeof (inner as { code: unknown }).code === 'string'
	);
}
