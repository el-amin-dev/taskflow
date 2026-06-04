import { request } from './transport';
import type { components } from './types';

type MemberResponse = components['schemas']['MemberResponse'];
type MemberInvite = components['schemas']['MemberInvite'];

// POST /v1/workspaces/{id}/members — invite a member by email with a role.
// Admin-only on the backend; returns the new membership.
//
// NOTE: there is no GET /members (returns 405) and no usable list endpoint,
// so the frontend can invite but not display members yet. Tracked backend gap.
export function invite(
	accessToken: string,
	workspaceId: string,
	body: MemberInvite
): Promise<MemberResponse> {
	return request<MemberResponse>(`/v1/workspaces/${workspaceId}/members`, {
		method: 'POST',
		body,
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
