import { request } from './transport';
import type { components } from './types';

type TaskResponse = components['schemas']['TaskResponse'];
type TaskCreate = components['schemas']['TaskCreate'];
type TaskUpdate = components['schemas']['TaskUpdate'];

// GET /v1/workspaces/{id}/tasks — tasks in a workspace the caller belongs to.
export function list(accessToken: string, workspaceId: string): Promise<TaskResponse[]> {
	return request<TaskResponse[]>(`/v1/workspaces/${workspaceId}/tasks`, {
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}

// POST /v1/workspaces/{id}/tasks — create a task. Returns the new task.
export function create(
	accessToken: string,
	workspaceId: string,
	body: TaskCreate
): Promise<TaskResponse> {
	return request<TaskResponse>(`/v1/workspaces/${workspaceId}/tasks`, {
		method: 'POST',
		body,
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
// PATCH /v1/workspaces/{id}/tasks/{taskId} — partial update (any subset of
// fields). Returns the updated task.
export function update(
	accessToken: string,
	workspaceId: string,
	taskId: string,
	body: TaskUpdate
): Promise<TaskResponse> {
	return request<TaskResponse>(`/v1/workspaces/${workspaceId}/tasks/${taskId}`, {
		method: 'PATCH',
		body,
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}

// DELETE /v1/workspaces/{id}/tasks/{taskId} — remove a task. Returns 204.
export function remove(
	accessToken: string,
	workspaceId: string,
	taskId: string
): Promise<void> {
	return request<void>(`/v1/workspaces/${workspaceId}/tasks/${taskId}`, {
		method: 'DELETE',
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
