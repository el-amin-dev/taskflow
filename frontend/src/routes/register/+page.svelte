<script lang="ts">
	import { goto } from '$app/navigation';
	import type { ErrorCode } from '$lib/api/errors';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let submitting = $state(false);

	// Map the backend's machine code to a friendly message. Branch on code,
	// never on the prose (the contract is the code — see API.md).
	function messageFor(code: ErrorCode | string): string {
		switch (code) {
			case 'email_unavailable':
				return 'An account with this email already exists.';
			case 'invalid_request':
				return 'Check your email and password (8–128 characters).';
			default:
				return 'Something went wrong. Please try again.';
		}
	}

	async function submit(event: Event) {
		event.preventDefault();
		error = '';
		submitting = true;

		try {
			const res = await fetch('/api/auth/register', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});

			if (res.ok) {
				await goto('/', { invalidateAll: true });
				return;
			}

			const body = await res.json().catch(() => ({}));
			error = messageFor(body.code ?? 'unknown');
		} catch {
			error = 'Could not reach the server. Please try again.';
		} finally {
			submitting = false;
		}
	}
</script>

<section class="mx-auto max-w-sm py-8 md:py-12">
	<h1 class="text-2xl font-semibold text-gray-900">Create your account</h1>
	<p class="mt-2 text-sm text-gray-600">Start managing your team's work.</p>

	<form class="mt-6 flex flex-col gap-4" onsubmit={submit}>
		<label class="flex flex-col gap-1">
			<span class="text-sm font-medium text-gray-700">Email</span>
			<input type="email" bind:value={email} required autocomplete="email" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none" />
		</label>

		<label class="flex flex-col gap-1">
			<span class="text-sm font-medium text-gray-700">Password</span>
			<input type="password" bind:value={password} required minlength="8" maxlength="128" autocomplete="new-password" class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none" />
		</label>

		{#if error}
			<p class="text-sm text-red-700">{error}</p>
		{/if}

		<button type="submit" disabled={submitting} class="rounded-md bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50">
			{submitting ? 'Creating account…' : 'Create account'}
		</button>
	</form>

	<p class="mt-4 text-sm text-gray-600">
		Already have an account? <a href="/login" class="font-medium text-gray-900 underline">Log in</a>
	</p>
</section>
