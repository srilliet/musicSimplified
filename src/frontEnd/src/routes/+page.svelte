<script lang="ts">
	import Card from '$lib/components/ui/card.svelte';
	import CardHeader from '$lib/components/ui/card-header.svelte';
	import CardTitle from '$lib/components/ui/card-title.svelte';
	import CardContent from '$lib/components/ui/card-content.svelte';
</script>

<h2 class="text-3xl font-bold mb-6">Home</h2>

<div class="space-y-6">
	<Card class="border-2 border-white">
		<CardHeader>
			<CardTitle>Welcome to MusicSimplify</CardTitle>
		</CardHeader>
		<CardContent>
			<p class="text-muted-foreground">Your music management system</p>
		</CardContent>
	</Card>
</div>
