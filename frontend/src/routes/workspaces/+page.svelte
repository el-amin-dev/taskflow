<script lang="ts">
	import { enhance } from '$app/forms';
	import type { SubmitFunction } from '@sveltejs/kit';

	let { data, form } = $props();

	let showForm = $state(false);
	let submitting = $state(false);

	// Collapse + reset the form after a successful create.
	const handleSubmit: SubmitFunction = () => {
		submitting = true;
		return async ({ result, update }) => {
			submitting = false;
			await update();
			if (result.type === 'success') {
				showForm = false;
			}
		};
	};
</script>

<section class="mx-auto max-w-2xl py-6 md:py-10">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-gray-900">Your workspaces</h1>
			<p class="mt-2 text-sm text-gray-600">Workspaces you belong to.</p>
		</div>
		{#if !showForm}
			<button onclick={() => (showForm = true)} class="shrink-0 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">New workspace</button>
		{/if}
	</div>

	{#if showForm}
		<form method="POST" use:enhance={handleSubmit} class="mt-6 flex flex-col gap-3 rounded-md border border-gray-200 bg-white p-4">
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium text-gray-700">Workspace name</span>
				<input name="name" required value={form?.name ?? ''} placeholder="e.g. Engineering" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none" />
			</label>

			{#if form?.error}
				<p class="text-sm text-red-700">{form.error}</p>
			{/if}

			<div class="flex gap-2">
				<button type="submit" disabled={submitting} class="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50">
					{submitting ? 'Creating…' : 'Create'}
				</button>
				<button type="button" onclick={() => (showForm = false)} class="rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">Cancel</button>
			</div>
		</form>
	{/if}

	{#if data.loadError}
		<p class="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
			Couldn't load your workspaces. Please refresh to try again.
		</p>
	{:else if data.workspaces.length === 0}
		<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
			<p class="text-sm font-medium text-gray-900">No workspaces yet</p>
			<p class="mt-1 text-sm text-gray-600">Create one with the button above to get started.</p>
		</div>
	{:else}
		<ul class="mt-6 flex flex-col gap-2">
			{#each data.workspaces as ws (ws.id)}
				<li class="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3">
					<div class="min-w-0">
						<p class="truncate text-sm font-medium text-gray-900">{ws.name}</p>
						<p class="text-xs text-gray-500">Created {new Date(ws.created_at).toLocaleDateString()}</p>
					</div>
					{#if ws.owner_id === data.user.id}
						<span class="ml-3 shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">Owner</span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</section>
