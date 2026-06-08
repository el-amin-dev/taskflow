<script lang="ts">
	import { enhance } from '$app/forms';
	import type { SubmitFunction } from '@sveltejs/kit';

	let { data, form } = $props();

	let showInvite = $state(false);
	let submitting = $state(false);

	const handleInvite: SubmitFunction = () => {
		submitting = true;
		return async ({ result, update }) => {
			submitting = false;
			await update();
			if (result.type === 'success') {
				showInvite = false;
			}
		};
	};
</script>

<section class="mx-auto max-w-2xl py-6 md:py-10">
	<a href="/workspaces" class="text-sm text-gray-600 hover:text-gray-900">&larr; Back to workspaces</a>

	{#if data.loadError}
		<p class="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
			Couldn't load this workspace. Please refresh to try again.
		</p>
	{:else if data.notFound || !data.workspace}
		<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
			<p class="text-sm font-medium text-gray-900">Workspace not found</p>
			<p class="mt-1 text-sm text-gray-600">It may not exist, or you may not have access to it.</p>
		</div>
	{:else}
		<div class="mt-4">
			<div class="flex items-center gap-3">
				<h1 class="text-2xl font-semibold text-gray-900">{data.workspace.name}</h1>
				{#if data.workspace.owner_id === data.user.id}
					<span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">Owner</span>
				{/if}
			</div>

			<dl class="mt-6 flex flex-col gap-3 text-sm">
				<div class="flex justify-between border-b border-gray-100 pb-2">
					<dt class="text-gray-500">Created</dt>
					<dd class="text-gray-900">{new Date(data.workspace.created_at).toLocaleDateString()}</dd>
				</div>
				<div class="flex justify-between border-b border-gray-100 pb-2">
					<dt class="text-gray-500">Workspace ID</dt>
					<dd class="font-mono text-xs text-gray-600">{data.workspace.id}</dd>
				</div>
                     </dl>

			<a href="/workspaces/{data.workspace.id}/tasks" class="mt-6 flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3 hover:border-gray-400 hover:bg-gray-50">
				<span class="text-sm font-medium text-gray-900">View tasks</span>
				<span class="text-gray-400">&rarr;</span>
			</a>

			<div class="mt-8">
				<div class="flex items-center justify-between">
					<h2 class="text-lg font-semibold text-gray-900">Members</h2>
					{#if !showInvite}
						<button onclick={() => (showInvite = true)} class="shrink-0 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">Invite member</button>
					{/if}
				</div>

				{#if form?.invited}
					<p class="mt-3 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
						Invited {form.email} as {form.role}.
					</p>
				{/if}

				{#if showInvite}
					<form method="POST" action="?/invite" use:enhance={handleInvite} class="mt-3 flex flex-col gap-3 rounded-md border border-gray-200 bg-white p-4">
						<label class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-700">Email</span>
							<input name="email" type="email" required value={form?.email ?? ''} placeholder="person@example.com" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none" />
						</label>
						<label class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-700">Role</span>
							<select name="role" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none">
								<option value="member">Member</option>
								<option value="admin">Admin</option>
								<option value="viewer">Viewer</option>
							</select>
						</label>

						{#if form?.error}
							<p class="text-sm text-red-700">{form.error}</p>
						{/if}

						<div class="flex gap-2">
							<button type="submit" disabled={submitting} class="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50">
								{submitting ? 'Inviting…' : 'Send invite'}
							</button>
							<button type="button" onclick={() => (showInvite = false)} class="rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">Cancel</button>
						</div>
					</form>
				{/if}

				<p class="mt-4 text-sm text-gray-500">
					The member list isn't available yet — the backend doesn't expose a way to fetch members.
				</p>
			</div>
		</div>
	{/if}
</section>
