<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getPlaylistTracks, removeTrackFromPlaylist } from '$lib/api/tracks';
	import type { PlaylistTrack } from '$lib/api/tracks';
	import Table from '$lib/components/ui/table.svelte';
	import TableHeader from '$lib/components/ui/table-header.svelte';
	import TableBody from '$lib/components/ui/table-body.svelte';
	import TableRow from '$lib/components/ui/table-row.svelte';
	import TableHead from '$lib/components/ui/table-head.svelte';
	import TableCell from '$lib/components/ui/table-cell.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import CardHeader from '$lib/components/ui/card-header.svelte';
	import CardTitle from '$lib/components/ui/card-title.svelte';
	import CardContent from '$lib/components/ui/card-content.svelte';
	import { ArrowLeft, Music, Trash2 } from 'lucide-svelte';

	let playlistId = $derived.by(() => {
		const id = $page.params.id;
		if (!id) return null;
		const numId = Number(id);
		return isNaN(numId) ? null : numId;
	});
	let playlist = $state<{ id: number; name: string; description: string | null; created_at: string; updated_at: string; track_count: number } | null>(null);
	let tracks = $state<PlaylistTrack[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let removingTrackId = $state<number | null>(null);

	async function loadPlaylistTracks() {
		if (!playlistId) {
			error = 'Invalid playlist ID';
			loading = false;
			return;
		}

		loading = true;
		error = null;

		try {
			console.log('Loading playlist tracks for ID:', playlistId);
			const data = await getPlaylistTracks(playlistId);
			console.log('Playlist tracks loaded:', data);
			playlist = data.playlist;
			tracks = data.tracks;
		} catch (err) {
			console.error('Error loading playlist tracks:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to load playlist tracks';
			}
		} finally {
			loading = false;
		}
	}

	async function handleRemoveTrack(trackId: number) {
		if (!confirm('Remove this track from the playlist?')) {
			return;
		}

		removingTrackId = trackId;
		error = null;

		try {
			await removeTrackFromPlaylist(playlistId, trackId);
			// Reload the playlist tracks
			await loadPlaylistTracks();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to remove track from playlist';
			}
			console.error('Error removing track from playlist:', err);
		} finally {
			removingTrackId = null;
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Watch for playlistId changes and reload tracks
	$effect(() => {
		if (playlistId) {
			// Clear previous data when playlist ID changes
			playlist = null;
			tracks = [];
			error = null;
			loadPlaylistTracks();
		}
	});
</script>

<div class="flex flex-col h-[calc(100vh-80px)] overflow-hidden">
	<!-- Header -->
	<div class="mb-4 flex-shrink-0 flex items-center gap-4">
		<Button variant="ghost" size="sm" href="/playlist">
			<ArrowLeft class="h-4 w-4 mr-2" />
			Back to Playlists
		</Button>
		{#if playlist}
			<h2 class="text-3xl font-bold">{playlist.name}</h2>
		{:else}
			<h2 class="text-3xl font-bold">Playlist</h2>
		{/if}
	</div>

	{#if error}
		<div class="text-destructive bg-destructive/10 border border-destructive rounded-md p-4 mb-4">
			{error}
		</div>
	{/if}

	<!-- Playlist Info Card -->
	{#if playlist}
		<Card class="border-2 border-white mb-4 flex-shrink-0">
			<CardHeader>
				<CardTitle>{playlist.name}</CardTitle>
			</CardHeader>
			<CardContent>
				<div class="flex items-center gap-4 text-sm text-muted-foreground">
					<span>{playlist.track_count} track{playlist.track_count !== 1 ? 's' : ''}</span>
					<span>Created {formatDate(playlist.created_at)}</span>
					{#if playlist.description}
						<span class="italic">{playlist.description}</span>
					{/if}
				</div>
			</CardContent>
		</Card>
	{/if}

	<!-- Tracks Table Card -->
	<Card class="border-2 border-white flex-1 flex flex-col min-h-0 overflow-hidden">
		<CardHeader class="flex-shrink-0 pb-3">
			<CardTitle>Tracks</CardTitle>
		</CardHeader>
		<CardContent class="flex-1 flex flex-col min-h-0 overflow-hidden">
			{#if loading}
				<div class="flex-1 flex items-center justify-center">
					<div class="text-center text-muted-foreground">Loading tracks...</div>
				</div>
			{:else if tracks.length === 0}
				<div class="flex-1 flex items-center justify-center">
					<div class="flex flex-col items-center text-center text-muted-foreground">
						<Music class="h-12 w-12 mb-4" />
						<p class="text-lg font-medium mb-2">No tracks in this playlist</p>
						<p class="text-sm">Add tracks from your library to get started</p>
					</div>
				</div>
			{:else}
				<div class="flex-1 flex flex-col min-h-0 overflow-hidden">
					<div class="flex-1 overflow-y-auto min-h-0">
						<Table class="border-2 border-white">
							<TableHeader>
								<TableRow>
									<TableHead class="w-16">#</TableHead>
									<TableHead>Artist</TableHead>
									<TableHead>Track Name</TableHead>
									<TableHead>Album</TableHead>
									<TableHead>Genre</TableHead>
									<TableHead>Relative Path</TableHead>
									<TableHead>Added</TableHead>
									<TableHead class="w-24">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{#each tracks as track, index}
									<TableRow>
										<TableCell class="text-muted-foreground">
											{track.position + 1}
										</TableCell>
										<TableCell class="font-medium">{track.artist_name || '-'}</TableCell>
										<TableCell>{track.track_name}</TableCell>
										<TableCell class="text-muted-foreground">
											{track.album || '-'}
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.genre || '-'}
										</TableCell>
										<TableCell class="text-muted-foreground text-sm">
											{track.relative_path || '-'}
										</TableCell>
										<TableCell class="text-muted-foreground text-sm">
											{formatDate(track.added_at)}
										</TableCell>
										<TableCell>
											<Button
												variant="ghost"
												size="sm"
												onclick={() => handleRemoveTrack(track.id)}
												disabled={removingTrackId === track.id}
											>
												<Trash2 class="h-4 w-4" />
											</Button>
										</TableCell>
									</TableRow>
								{/each}
							</TableBody>
						</Table>
					</div>
				</div>
			{/if}
		</CardContent>
	</Card>
</div>
