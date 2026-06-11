<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';

	let { children, data } = $props();

	let loggingOut = $state(false);

	async function logout() {
		loggingOut = true;
		try {
			await fetch('/api/auth/logout', { method: 'POST' });
			await goto('/', { invalidateAll: true });
		} finally {
			loggingOut = false;
		}
	}
</script>

<svelte:head>
	<title>TaskFlow</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<header class="border-b border-gray-200 bg-white">
	<div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 md:px-6">
		<a href="/" class="text-lg font-semibold text-gray-900">TaskFlow</a>
		<nav class="flex items-center gap-2 md:gap-3">
			{#if data.user}
				<span class="hidden text-sm text-gray-600 sm:inline">{data.user.email}</span>
				<button onclick={logout} disabled={loggingOut} class="rounded-md px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50">
					{loggingOut ? 'Logging out…' : 'Log out'}
				</button>
			{:else}
				<a href="/login" class="rounded-md px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100">Login</a>
				<a href="/register" class="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800">Sign up</a>
			{/if}
		</nav>
	</div>
</header>

<main class="mx-auto max-w-5xl px-4 py-6 md:px-6 md:py-10">
	{@render children()}
</main>
