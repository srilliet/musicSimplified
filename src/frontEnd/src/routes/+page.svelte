<script lang="ts">
	import Card from '$lib/components/ui/card.svelte';
	import CardHeader from '$lib/components/ui/card-header.svelte';
	import CardTitle from '$lib/components/ui/card-title.svelte';
	import CardContent from '$lib/components/ui/card-content.svelte';
</script>

<div class="space-y-6">
	<Card>
		<CardHeader>
			<CardTitle>Welcome to MusicSimplify</CardTitle>
		</CardHeader>
		<CardContent>
			<p class="text-muted-foreground">Your music management system</p>
		</CardContent>
	</Card>
</div>
