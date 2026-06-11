<script lang="ts">
	import type { PageServerData } from './$types';

	let { data }: { data: PageServerData } = $props();
</script>
<svelte:head><title>Health — TaskFlow</title></svelte:head>
<h1 class="text-2xl font-semibold">Backend health</h1>

{#if data.ok}
	<p class="mt-2 text-sm text-green-700">Reachable.</p>
	<dl class="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
		<dt class="text-gray-500">status</dt>
		<dd class="font-mono text-gray-900">{data.health.status}</dd>
		<dt class="text-gray-500">uptime</dt>
		<dd class="font-mono text-gray-900">{data.health.uptime_seconds.toFixed(1)}s</dd>
	</dl>
{:else}
	<p class="mt-2 text-sm text-red-700">Unreachable.</p>
	<dl class="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
		<dt class="text-gray-500">code</dt>
		<dd class="font-mono text-gray-900">{data.code}</dd>
		<dt class="text-gray-500">status</dt>
		<dd class="font-mono text-gray-900">{data.status}</dd>
		<dt class="text-gray-500">message</dt>
		<dd class="font-mono text-gray-900">{data.message}</dd>
	</dl>
{/if}
