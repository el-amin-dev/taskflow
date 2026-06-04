<script lang="ts">
	let { data } = $props();
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

			<p class="mt-8 text-sm text-gray-500">Members and tasks will live here.</p>
		</div>
	{/if}
</section>

