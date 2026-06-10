<script lang="ts">
	let { data } = $props();

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
		<a href="/workspaces/{data.workspace.id}/tasks" class="text-sm text-gray-600 hover:text-gray-900">&larr; Back to tasks</a>
	{:else}
		<a href="/workspaces" class="text-sm text-gray-600 hover:text-gray-900">&larr; Back to workspaces</a>
	{/if}

	{#if data.loadError}
		<p class="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
			Couldn't load this task. Please refresh to try again.
		</p>
	{:else if data.notFound || !data.task}
		<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
			<p class="text-sm font-medium text-gray-900">Task not found</p>
			<p class="mt-1 text-sm text-gray-600">It may not exist, or you may not have access to it.</p>
		</div>
	{:else}
		<div class="mt-4 flex items-start justify-between gap-3">
			<h1 class="text-2xl font-semibold text-gray-900">{data.task.title}</h1>
			<span class="mt-1 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {statusMeta(data.task.status).classes}">
				{statusMeta(data.task.status).label}
			</span>
		</div>

		{#if data.task.description}
			<p class="mt-3 text-sm text-gray-700">{data.task.description}</p>
		{:else}
			<p class="mt-3 text-sm text-gray-400">No description.</p>
		{/if}

		<p class="mt-2 text-xs text-gray-500">Created {new Date(data.task.created_at).toLocaleDateString()}</p>

		<h2 class="mt-8 text-lg font-semibold text-gray-900">Comments</h2>
		<p class="mt-2 text-sm text-gray-500">{data.comments.length} comment{data.comments.length === 1 ? '' : 's'}</p>
		<!-- comments list + add form arrive in the next commits -->
	{/if}
</section>
