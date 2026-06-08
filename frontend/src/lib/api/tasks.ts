import { request } from './transport';
import type { components } from './types';

type TaskResponse = components['schemas']['TaskResponse'];
type TaskCreate = components['schemas']['TaskCreate'];

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
