<script lang="ts">
	let { data } = $props();

	// Map status -> label + badge classes. Keeps the enum's presentation in one place.
	const STATUS_META: Record<string, { label: string; classes: string }> = {
		todo: { label: 'To do', classes: 'bg-gray-100 text-gray-700' },
		in_progress: { label: 'In progress', classes: 'bg-blue-50 text-blue-700' },
		done: { label: 'Done', classes: 'bg-green-50 text-green-700' }
	};

	function statusMeta(status: string) {
		return STATUS_META[status] ?? { label: status, classes: 'bg-gray-100 text-gray-700' };
	}
</script>

<section class="mx-auto max-w-2xl py-6 md:py-10">
	{#if data.workspace}
		<a href="/workspaces/{data.workspace.id}" class="text-sm text-gray-600 hover:text-gray-900">&larr; Back to workspace</a>
	{:else}
		<a href="/workspaces" class="text-sm text-gray-600 hover:text-gray-900">&larr; Back to workspaces</a>
	{/if}

	{#if data.loadError}
		<p class="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
			Couldn't load tasks. Please refresh to try again.
		</p>
	{:else if data.notFound || !data.workspace}
		<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
			<p class="text-sm font-medium text-gray-900">Workspace not found</p>
			<p class="mt-1 text-sm text-gray-600">It may not exist, or you may not have access to it.</p>
		</div>
	{:else}
		<h1 class="mt-4 text-2xl font-semibold text-gray-900">Tasks</h1>
		<p class="mt-2 text-sm text-gray-600">{data.workspace.name}</p>

		{#if data.tasks.length === 0}
			<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
				<p class="text-sm font-medium text-gray-900">No tasks yet</p>
				<p class="mt-1 text-sm text-gray-600">Create one to get started.</p>
			</div>
		{:else}
			<ul class="mt-6 flex flex-col gap-2">
				{#each data.tasks as task (task.id)}
					<li class="rounded-md border border-gray-200 bg-white px-4 py-3">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<p class="truncate text-sm font-medium text-gray-900">{task.title}</p>
								{#if task.description}
									<p class="mt-0.5 line-clamp-2 text-sm text-gray-600">{task.description}</p>
								{/if}
							</div>
							<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {statusMeta(task.status).classes}">
								{statusMeta(task.status).label}
							</span>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</section>
