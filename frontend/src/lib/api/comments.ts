import { request } from './transport';
import type { components } from './types';

type CommentPage = components['schemas']['CommentPage'];
type CommentResponse = components['schemas']['CommentResponse'];
type CommentCreate = components['schemas']['CommentCreate'];

// GET /v1/workspaces/{id}/tasks/{taskId}/comments — paginated comment page.
// v1 fetches the first page; cursor pagination (page.next_cursor) is deferred.
export function list(
	accessToken: string,
	workspaceId: string,
	taskId: string
): Promise<CommentPage> {
	return request<CommentPage>(`/v1/workspaces/${workspaceId}/tasks/${taskId}/comments`, {
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}

// POST /v1/workspaces/{id}/tasks/{taskId}/comments — add a comment. Returns it.
export function create(
	accessToken: string,
	workspaceId: string,
	taskId: string,
	body: CommentCreate
): Promise<CommentResponse> {
	return request<CommentResponse>(`/v1/workspaces/${workspaceId}/tasks/${taskId}/comments`, {
		method: 'POST',
		body,
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}

