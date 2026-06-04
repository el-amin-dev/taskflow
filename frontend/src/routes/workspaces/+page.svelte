<script lang="ts">
	let { data } = $props();
</script>

<section class="mx-auto max-w-2xl py-6 md:py-10">
	<h1 class="text-2xl font-semibold text-gray-900">Your workspaces</h1>
	<p class="mt-2 text-sm text-gray-600">Workspaces you belong to.</p>

	{#if data.loadError}
		<p class="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
			Couldn't load your workspaces. Please refresh to try again.
		</p>
	{:else if data.workspaces.length === 0}
		<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
			<p class="text-sm font-medium text-gray-900">No workspaces yet</p>
			<p class="mt-1 text-sm text-gray-600">Once you create or join one, it'll show up here.</p>
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
