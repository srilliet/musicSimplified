<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { login } from '$lib/api/auth';
	import Button from '$lib/components/ui/button.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import CardHeader from '$lib/components/ui/card-header.svelte';
	import CardTitle from '$lib/components/ui/card-title.svelte';
	import CardContent from '$lib/components/ui/card-content.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin() {
		error = '';
		loading = true;

		try {
			const response = await login(username, password);
			console.log('Login successful, updating store');
			authStore.login(response.token, response.user);
			console.log('Store updated, navigating to home');
			// Wait a tick to ensure store updates propagate
			await new Promise(resolve => setTimeout(resolve, 10));
			goto('/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Login failed';
			loading = false;
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter' && !loading) {
			handleLogin();
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-background p-4">
	<Card class="w-full max-w-md border-2 border-white">
		<CardHeader>
			<CardTitle class="text-2xl text-center">MusicSimplify</CardTitle>
		</CardHeader>
		<CardContent class="space-y-4">
			{#if error}
				<div class="text-destructive text-sm text-center bg-destructive/10 p-3 rounded-md">
					{error}
				</div>
			{/if}

			<div class="space-y-2">
				<label for="username" class="text-sm font-medium">Username</label>
				<input
					id="username"
					type="text"
					placeholder="Enter your username"
					class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
					bind:value={username}
					onkeypress={handleKeyPress}
					disabled={loading}
					autocomplete="username"
				/>
			</div>

			<div class="space-y-2">
				<label for="password" class="text-sm font-medium">Password</label>
				<input
					id="password"
					type="password"
					placeholder="Enter your password"
					class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
					bind:value={password}
					onkeypress={handleKeyPress}
					disabled={loading}
					autocomplete="current-password"
				/>
			</div>

			<Button
				class="w-full"
				onclick={handleLogin}
				disabled={loading || !username.trim() || !password.trim()}
			>
				{loading ? 'Logging in...' : 'Login'}
			</Button>
		</CardContent>
	</Card>
</div>
