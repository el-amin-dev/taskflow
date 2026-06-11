<script lang="ts">
	import { enhance } from '$app/forms';
	import type { SubmitFunction } from '@sveltejs/kit';

	let { data, form } = $props();

	let showForm = $state(false);
	let submitting = $state(false);

	const handleCreate: SubmitFunction = () => {
		submitting = true;
		return async ({ result, update }) => {
			submitting = false;
			await update();
			if (result.type === 'success') {
				showForm = false;
			}
		};
	};
	const handleDelete: SubmitFunction = ({ cancel }) => {
		if (!confirm('Delete this task? This cannot be undone.')) {
			cancel();
			return;
		}
		return async ({ update }) => {
			await update();
		};
	};

	const STATUS_META: Record<string, { label: string; classes: string }> = {
		todo: { label: 'To do', classes: 'bg-gray-100 text-gray-700' },
		in_progress: { label: 'In progress', classes: 'bg-blue-50 text-blue-700' },
		done: { label: 'Done', classes: 'bg-green-50 text-green-700' }
	};

	function statusMeta(status: string) {
		return STATUS_META[status] ?? { label: status, classes: 'bg-gray-100 text-gray-700' };
	}
</script>

<svelte:head><title>Tasks · {data.workspace?.name ?? 'Workspace'} — TaskFlow</title></svelte:head>

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
		<div class="mt-4 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900">Tasks</h1>
				<p class="mt-2 text-sm text-gray-600">{data.workspace.name}</p>
			</div>
			{#if !showForm}
				<button onclick={() => (showForm = true)} class="shrink-0 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">New task</button>
			{/if}
		</div>

		{#if showForm}
			<form method="POST" action="?/create" use:enhance={handleCreate} class="mt-6 flex flex-col gap-3 rounded-md border border-gray-200 bg-white p-4">
				<label class="flex flex-col gap-1">
					<span class="text-sm font-medium text-gray-700">Title</span>
					<input name="title" required value={form?.title ?? ''} placeholder="e.g. Write the report" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none" />
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm font-medium text-gray-700">Description <span class="text-gray-400">(optional)</span></span>
					<textarea name="description" rows="2" value={form?.description ?? ''} class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"></textarea>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm font-medium text-gray-700">Status</span>
					<select name="status" value={form?.status ?? 'todo'} class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none">
						<option value="todo">To do</option>
						<option value="in_progress">In progress</option>
						<option value="done">Done</option>
					</select>
				</label>

				{#if form?.error}
					<p class="text-sm text-red-700">{form.error}</p>
				{/if}

				<div class="flex gap-2">
					<button type="submit" disabled={submitting} class="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50">
						{submitting ? 'Creating…' : 'Create task'}
					</button>
					<button type="button" onclick={() => (showForm = false)} class="rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">Cancel</button>
				</div>
			</form>
		{/if}

		{#if data.tasks.length === 0}
			<div class="mt-6 rounded-md border border-dashed border-gray-300 px-4 py-10 text-center">
				<p class="text-sm font-medium text-gray-900">No tasks yet</p>
				<p class="mt-1 text-sm text-gray-600">Create one with the button above to get started.</p>
			</div>
		{:else}
			<ul class="mt-6 flex flex-col gap-2">
				{#each data.tasks as task (task.id)}
					<li class="rounded-md border border-gray-200 bg-white px-4 py-3">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<a href="/workspaces/{data.workspace.id}/tasks/{task.id}" class="truncate block text-sm font-medium text-gray-900 hover:text-gray-600 hover:underline">{task.title}</a>
								{#if task.description}
									<p class="mt-0.5 line-clamp-2 text-sm text-gray-600">{task.description}</p>
								{/if}
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<form method="POST" action="?/updateStatus" use:enhance>
									<input type="hidden" name="task_id" value={task.id} />
									<select
										name="status"
										value={task.status}
										onchange={(e) => e.currentTarget.form?.requestSubmit()}
										class="rounded-full border-0 px-2 py-0.5 text-xs font-medium {statusMeta(task.status).classes} focus:outline-none focus:ring-1 focus:ring-gray-400"
									>
										<option value="todo">To do</option>
										<option value="in_progress">In progress</option>
										<option value="done">Done</option>
									</select>
								</form>
								<form method="POST" action="?/deleteTask" use:enhance={handleDelete}>
									<input type="hidden" name="task_id" value={task.id} />
									<button type="submit" aria-label="Delete task" class="rounded-md px-2 py-1 text-sm text-gray-400 hover:bg-red-50 hover:text-red-600">
										&times;
									</button>
								</form>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</section>
