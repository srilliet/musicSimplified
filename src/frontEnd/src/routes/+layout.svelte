<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';
	import Header from '$lib/components/header.svelte';
	import Sidebar from '$lib/components/sidebar.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen bg-background">
	<Header />
	<div class="flex pt-16">
		<Sidebar />
		<main class="flex-1 ml-64 p-6">
			{@render children()}
		</main>
	</div>
</div>
