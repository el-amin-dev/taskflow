import { request } from './transport';
import type { components } from './types';

// Convenience aliases — the generated types' nesting is awkward to spell out.
type RegisterRequest = components['schemas']['RegisterRequest'];
type LoginRequest = components['schemas']['LoginRequest'];
type RefreshRequest = components['schemas']['RefreshRequest'];
type LogoutRequest = components['schemas']['LogoutRequest'];
type UserResponse = components['schemas']['UserResponse'];
type TokenResponse = components['schemas']['TokenResponse'];

// POST /v1/auth/register — create account.
// Returns the new user. Does NOT return tokens — caller must log in
// separately, or the SvelteKit /api/auth/register route can chain
// register-then-login to issue cookies.
export function register(body: RegisterRequest): Promise<UserResponse> {
	return request<UserResponse>('/v1/auth/register', { method: 'POST', body });
}

// POST /v1/auth/login — exchange credentials for an access+refresh token pair.
// Body in the response carries both tokens; the SvelteKit server route
// translates them into httpOnly cookies before they ever reach the browser.
export function login(body: LoginRequest): Promise<TokenResponse> {
	return request<TokenResponse>('/v1/auth/login', { method: 'POST', body });
}

// GET /v1/auth/me — current user, identified by the Bearer token in the header.
// `accessToken` is forwarded from the server route after reading the cookie.
export function me(accessToken: string): Promise<UserResponse> {
	return request<UserResponse>('/v1/auth/me', {
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}

// POST /v1/auth/refresh — exchange a refresh token for a new pair.
// Single-use: the old refresh is invalidated server-side on success.
// On replay, backend kills the family (see backend SECURITY.md).
export function refresh(body: RefreshRequest): Promise<TokenResponse> {
	return request<TokenResponse>('/v1/auth/refresh', { method: 'POST', body });
}

// POST /v1/auth/logout — revoke the refresh token server-side.
// Returns 204; transport returns undefined.
export function logout(body: LogoutRequest): Promise<void> {
	return request<void>('/v1/auth/logout', { method: 'POST', body });
}
