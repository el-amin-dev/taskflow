import { request } from './transport';
import type { components } from './types';

type WorkspaceResponse = components['schemas']['WorkspaceResponse'];
type WorkspaceCreate = components['schemas']['WorkspaceCreate'];

// GET /v1/workspaces — the workspaces the caller is a member of.
// `accessToken` is forwarded from the server route after reading the cookie,
// same as auth.me. Returns an array (empty if the user has no workspaces).
export function list(accessToken: string): Promise<WorkspaceResponse[]> {
	return request<WorkspaceResponse[]>('/v1/workspaces', {
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
// POST /v1/workspaces — create a workspace; the caller becomes its owner.
// Authenticated like list: token forwarded from the server-side caller. 
export function create(accessToken: string, body: WorkspaceCreate): Promise<WorkspaceResponse> {
	return request<WorkspaceResponse>('/v1/workspaces', {
		method: 'POST',
		body,                                              
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
