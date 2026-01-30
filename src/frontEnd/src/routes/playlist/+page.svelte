<script lang="ts">
	import { onMount } from 'svelte';
	import { getPlaylists, createPlaylist, deletePlaylist } from '$lib/api/tracks';
	import { playlistsStore } from '$lib/stores/playlists';
	import type { Playlist } from '$lib/schema';
	import Card from '$lib/components/ui/card.svelte';
	import CardHeader from '$lib/components/ui/card-header.svelte';
	import CardTitle from '$lib/components/ui/card-title.svelte';
	import CardContent from '$lib/components/ui/card-content.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Input from '$lib/components/ui/input.svelte';
	import { Plus, Trash2, Music } from 'lucide-svelte';

	let playlists = $state<Playlist[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let showCreateDialog = $state(false);
	let newPlaylistName = $state('');
	let creating = $state(false);
	let deletingPlaylistId = $state<number | null>(null);

	async function loadPlaylists() {
		loading = true;
		error = null;

		try {
			const data = await getPlaylists();
			playlists = data.playlists;
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
				console.error('Error loading playlists:', err);
			} else {
				error = 'Failed to load playlists';
				console.error('Unknown error:', err);
			}
		} finally {
			loading = false;
		}
	}

	async function handleCreatePlaylist() {
		console.log('handleCreatePlaylist called', { newPlaylistName, creating });
		
		if (!newPlaylistName.trim()) {
			error = 'Playlist name is required';
			return;
		}

		creating = true;
		error = null;

		try {
			console.log('Creating playlist with name:', newPlaylistName);
			const playlist = await createPlaylist(newPlaylistName);
			console.log('Playlist created:', playlist);
			playlists = [playlist, ...playlists];
			newPlaylistName = '';
			showCreateDialog = false;
			// Refresh the playlists store so sidebar updates
			await playlistsStore.load();
		} catch (err) {
			console.error('Error creating playlist:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to create playlist';
			}
		} finally {
			creating = false;
		}
	}

	async function handleDeletePlaylist(playlistId: number) {
		if (!confirm('Are you sure you want to delete this playlist?')) {
			return;
		}

		deletingPlaylistId = playlistId;
		error = null;

		try {
			await deletePlaylist(playlistId);
			playlists = playlists.filter((p) => p.id !== playlistId);
			// Refresh the playlists store so sidebar updates
			await playlistsStore.load();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
				console.error('Error deleting playlist:', err);
			} else {
				error = 'Failed to delete playlist';
				console.error('Unknown error:', err);
			}
		} finally {
			deletingPlaylistId = null;
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	onMount(() => {
		loadPlaylists();
	});
</script>

<h2 class="text-3xl font-bold mb-6">Playlists</h2>

<div class="space-y-6">
	<!-- Create Playlist Card -->
	<Card class="border-2 border-white">
		<CardHeader>
			<div class="flex justify-between items-center">
				<CardTitle>Create New Playlist</CardTitle>
				<Button
					variant="default"
					size="sm"
					type="button"
					onclick={() => {
						showCreateDialog = !showCreateDialog;
						if (!showCreateDialog) {
							newPlaylistName = '';
						}
					}}
				>
					<Plus class="h-4 w-4 mr-2" />
					{showCreateDialog ? 'Cancel' : 'New Playlist'}
				</Button>
			</div>
		</CardHeader>
		{#if showCreateDialog}
			<CardContent class="space-y-4">
				<div>
					<label for="playlist-name" class="block text-sm font-medium mb-2">
						Playlist Name <span class="text-destructive">*</span>
					</label>
					<input
						id="playlist-name"
						type="text"
						placeholder="Enter playlist name"
						class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
						bind:value={newPlaylistName}
						disabled={creating}
						onkeydown={(e) => {
							if (e.key === 'Enter' && newPlaylistName.trim() && !creating) {
								e.preventDefault();
								handleCreatePlaylist();
							}
						}}
					/>
				</div>
				<button
					type="button"
					class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
					onclick={() => {
						console.log('Button clicked, newPlaylistName:', newPlaylistName);
						handleCreatePlaylist();
					}}
					disabled={creating || !newPlaylistName.trim()}
				>
					{creating ? 'Creating...' : 'Create Playlist'}
				</button>
			</CardContent>
		{/if}
	</Card>

	{#if error}
		<div class="text-destructive bg-destructive/10 border border-destructive rounded-md p-4">
			{error}
		</div>
	{/if}

	<!-- Playlists List Card -->
	<Card class="border-2 border-white">
		<CardHeader>
			<CardTitle>My Playlists ({playlists.length})</CardTitle>
		</CardHeader>
		<CardContent>
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="text-center text-muted-foreground">Loading playlists...</div>
				</div>
			{:else if playlists.length === 0}
				<div class="flex flex-col items-center justify-center py-12">
					<Music class="h-12 w-12 text-muted-foreground mb-4" />
					<div class="text-center text-muted-foreground">
						<p class="text-lg font-medium mb-2">No playlists yet</p>
						<p class="text-sm">Create your first playlist to get started</p>
					</div>
				</div>
			{:else}
				<div class="space-y-3">
					{#each playlists as playlist}
						<div
							class="flex items-center justify-between p-4 border border-border rounded-md hover:bg-accent/50 transition-colors"
						>
							<a
								href={`/playlist/${playlist.id}`}
								class="flex-1 cursor-pointer"
							>
								<div class="flex items-center gap-3 mb-1">
									<Music class="h-5 w-5 text-muted-foreground" />
									<h3 class="text-lg font-semibold hover:text-primary">{playlist.name}</h3>
								</div>
								<div class="flex items-center gap-4 text-xs text-muted-foreground ml-8">
									<span>{playlist.track_count} track{playlist.track_count !== 1 ? 's' : ''}</span>
									<span>Created {formatDate(playlist.created_at)}</span>
								</div>
							</a>
							<Button
								variant="ghost"
								size="sm"
								onclick={(e) => {
									e.preventDefault();
									e.stopPropagation();
									handleDeletePlaylist(playlist.id);
								}}
								disabled={deletingPlaylistId === playlist.id}
								class="text-destructive hover:text-destructive hover:bg-destructive/10"
							>
								<Trash2 class="h-4 w-4" />
							</Button>
						</div>
					{/each}
				</div>
			{/if}
		</CardContent>
	</Card>
</div>
