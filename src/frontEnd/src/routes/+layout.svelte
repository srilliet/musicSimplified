<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';
	import Header from '$lib/components/header.svelte';
	import Sidebar from '$lib/components/sidebar.svelte';
	import { authStore } from '$lib/stores/auth';

	let { children } = $props();
	
	// Get initial state from store
	let authState = $state(get(authStore));
	let isAuthenticated = $derived(authState.isAuthenticated);
	let isLoginPage = $derived($page.url.pathname === '/login');
	
	$effect(() => {
		const unsubscribe = authStore.subscribe((state) => {
			authState = state;
			console.log('Auth state updated:', state.isAuthenticated, state.user?.username);
		});
		return unsubscribe;
	});
	
	$effect(() => {
		if (typeof window === 'undefined') return;
		
		// Redirect to login if not authenticated and not already on login page
		if (!isAuthenticated && !isLoginPage) {
			console.log('Not authenticated, redirecting to login');
			goto('/login');
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if isAuthenticated}
	<div class="min-h-screen bg-background">
		<Header />
		<div class="flex pt-16">
			<Sidebar />
			<main class="flex-1 ml-64 p-6">
				{@render children()}
			</main>
		</div>
	</div>
{:else}
	{@render children()}
{/if}
