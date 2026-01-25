<script lang="ts">
	import { onMount } from 'svelte';
	import { getUserTracks, getUserTracksGenres, getUserTracksArtists, removeTrackFromLibrary, initializeUserLibrary, getRemovedTracks, restoreTrackToLibrary, restoreAllTracks, updateUserTrack, type RemovedTrack } from '$lib/api/tracks';
	import type { UserTrack, UserTracksPaginatedResponse } from '$lib/schema';
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
	import Checkbox from '$lib/components/ui/checkbox.svelte';
	import { ChevronLeft, ChevronRight, Search, X, Trash2, RotateCcw, Star, Heart } from 'lucide-svelte';

	let tracks = $state<UserTrack[]>([]);
	let currentPage = $state(1);
	let pageSize = $state(100);
	let totalPages = $state(1);
	let totalCount = $state(0);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let selectedGenre = $state<string>('');
	let selectedArtist = $state<string>('');
	let genres = $state<string[]>([]);
	let artists = $state<string[]>([]);
	let selectedTrackIds = $state<Set<number>>(new Set());
	let removingTrackId = $state<number | null>(null);
	let showRestoreDialog = $state(false);
	let removedTracks = $state<RemovedTrack[]>([]);
	let removedTracksPage = $state(1);
	let removedTracksTotalPages = $state(1);
	let removedTracksTotalCount = $state(0);
	let removedTracksLoading = $state(false);
	let removedTracksSearch = $state('');
	let restoringTrackId = $state<number | null>(null);
	let restoringAll = $state(false);

	async function loadTracks(page: number = 1) {
		loading = true;
		error = null;

		try {
			const data: UserTracksPaginatedResponse = await getUserTracks(page, pageSize, {
				search: searchQuery.trim() || undefined,
				genre: selectedGenre || undefined,
				artistName: selectedArtist || undefined
			});
			tracks = data.tracks;
			currentPage = data.page;
			totalPages = data.total_pages;
			totalCount = data.count;
			selectedTrackIds = new Set();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
				console.error('Error loading tracks:', err);
			} else {
				error = 'Failed to load tracks';
				console.error('Unknown error:', err);
			}
		} finally {
			loading = false;
		}
	}

	async function loadGenres() {
		try {
			genres = await getUserTracksGenres();
		} catch (err) {
			console.error('Error loading genres:', err);
		}
	}

	async function loadArtists() {
		try {
			artists = await getUserTracksArtists();
		} catch (err) {
			console.error('Error loading artists:', err);
		}
	}

	async function handleRemoveTrack(trackId: number) {
		if (!confirm('Remove this track from your library?')) {
			return;
		}

		removingTrackId = trackId;
		try {
			await removeTrackFromLibrary(trackId);
			await loadTracks(currentPage);
			await loadGenres();
			await loadArtists();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to remove track';
			}
			console.error('Error removing track:', err);
		} finally {
			removingTrackId = null;
		}
	}

	async function loadRemovedTracks(page: number = 1) {
		removedTracksLoading = true;
		try {
			const data = await getRemovedTracks(page, 50, removedTracksSearch.trim() || undefined);
			removedTracks = data.tracks;
			removedTracksPage = data.page;
			removedTracksTotalPages = data.total_pages;
			removedTracksTotalCount = data.count;
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to load removed tracks';
			}
			console.error('Error loading removed tracks:', err);
		} finally {
			removedTracksLoading = false;
		}
	}

	async function handleRestoreTrack(trackId: number) {
		restoringTrackId = trackId;
		try {
			await restoreTrackToLibrary(trackId);
			await loadRemovedTracks(removedTracksPage);
			await loadTracks(currentPage);
			await loadGenres();
			await loadArtists();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to restore track';
			}
			console.error('Error restoring track:', err);
		} finally {
			restoringTrackId = null;
		}
	}

	async function handleRestoreAll() {
		if (!confirm(`Restore all ${removedTracksTotalCount} removed tracks to your library?`)) {
			return;
		}

		restoringAll = true;
		try {
			const result = await restoreAllTracks();
			await loadRemovedTracks(1);
			await loadTracks(currentPage);
			await loadGenres();
			await loadArtists();
			alert(result.message);
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to restore all tracks';
			}
			console.error('Error restoring all tracks:', err);
		} finally {
			restoringAll = false;
		}
	}

	async function handleRatingChange(trackId: number, rating: number) {
		try {
			// If clicking the same rating, remove it (set to null)
			const track = tracks.find((t) => t.id === trackId);
			const newRating = track?.rating === rating ? null : rating;
			
			await updateUserTrack(trackId, { rating: newRating });
			await loadTracks(currentPage);
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to update rating';
			}
			console.error('Error updating rating:', err);
		}
	}

	async function handleFavoriteToggle(trackId: number) {
		try {
			const track = tracks.find((t) => t.id === trackId);
			const newFavorite = !track?.favorite;
			
			await updateUserTrack(trackId, { favorite: newFavorite });
			await loadTracks(currentPage);
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to update favorite';
			}
			console.error('Error updating favorite:', err);
		}
	}

	function openRestoreDialog() {
		showRestoreDialog = true;
		removedTracksSearch = '';
		loadRemovedTracks(1);
	}

	function closeRestoreDialog() {
		showRestoreDialog = false;
		removedTracks = [];
		removedTracksSearch = '';
	}

	function handleRemovedTracksSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		removedTracksSearch = target.value;
		clearTimeout((handleRemovedTracksSearchInput as any).timeout);
		(handleRemovedTracksSearchInput as any).timeout = setTimeout(() => {
			loadRemovedTracks(1);
		}, 500);
	}

	function goToPage(page: number) {
		if (page >= 1 && page <= totalPages) {
			loadTracks(page);
		}
	}

	function previousPage() {
		if (currentPage > 1) {
			goToPage(currentPage - 1);
		}
	}

	function nextPage() {
		if (currentPage < totalPages) {
			goToPage(currentPage + 1);
		}
	}

	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		searchQuery = target.value;
		// Debounce search - reload after user stops typing
		clearTimeout((handleSearchInput as any).timeout);
		(handleSearchInput as any).timeout = setTimeout(() => {
			loadTracks(1);
		}, 500);
	}

	function handleGenreChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		selectedGenre = target.value;
		loadTracks(1);
	}

	function handleArtistChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		selectedArtist = target.value;
		loadTracks(1);
	}

	function clearFilters() {
		searchQuery = '';
		selectedGenre = '';
		selectedArtist = '';
		loadTracks(1);
	}

	let allSelected = $derived(
		tracks.length > 0 && tracks.every((track) => selectedTrackIds.has(track.id))
	);

	function toggleSelectAll() {
		if (allSelected) {
			selectedTrackIds = new Set();
		} else {
			selectedTrackIds = new Set(tracks.map((track) => track.id));
		}
	}

	function toggleTrackSelection(trackId: number) {
		if (selectedTrackIds.has(trackId)) {
			selectedTrackIds.delete(trackId);
			selectedTrackIds = new Set(selectedTrackIds);
		} else {
			selectedTrackIds.add(trackId);
			selectedTrackIds = new Set(selectedTrackIds);
		}
	}

	onMount(async () => {
		try {
			await initializeUserLibrary();
		} catch (err) {
			console.error('Error initializing library:', err);
		}
		await Promise.all([loadTracks(1), loadGenres(), loadArtists()]);
	});
</script>

<h2 class="text-3xl font-bold mb-6">My Library</h2>

<div class="flex flex-col h-[calc(100vh-80px)] overflow-hidden">
	<!-- My Library Card -->
	<Card class="border-2 border-white flex-1 flex flex-col min-h-0 overflow-hidden">
		<CardHeader class="flex-shrink-0 pb-3">
			<div class="flex items-center justify-between">
				<CardTitle>My Library</CardTitle>
				<Button variant="outline" onclick={openRestoreDialog}>
					<RotateCcw class="h-4 w-4 mr-2" />
					Restore from All Tracks
				</Button>
			</div>
		</CardHeader>
		<CardContent class="flex-1 flex flex-col min-h-0 overflow-hidden">
			<!-- Filters -->
			<div class="mb-3 space-y-3 flex-shrink-0">
				<div class="flex gap-3 items-end">
					<!-- Search Input -->
					<div class="flex-1 relative">
						<Search class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
						<input
							type="text"
							placeholder="Search by artist or track name..."
							class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 pl-10"
							bind:value={searchQuery}
							oninput={handleSearchInput}
						/>
					</div>

					<!-- Genre Filter -->
					<div class="w-48">
						<select
							class="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
							bind:value={selectedGenre}
							onchange={handleGenreChange}
						>
							<option value="">All Genres</option>
							{#each genres as genre}
								<option value={genre}>{genre}</option>
							{/each}
						</select>
					</div>

					<!-- Artist Filter -->
					<div class="w-48">
						<select
							class="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
							bind:value={selectedArtist}
							onchange={handleArtistChange}
						>
							<option value="">All Artists</option>
							{#each artists as artist}
								<option value={artist}>{artist}</option>
							{/each}
						</select>
					</div>

					<!-- Clear Filters Button -->
					<button
						type="button"
						class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-9 px-3 border border-input bg-background hover:bg-accent hover:text-accent-foreground"
						onclick={() => {
							console.log('Clear filters clicked');
							clearFilters();
						}}
						disabled={!searchQuery.trim() && !selectedGenre && !selectedArtist}
					>
						<X class="h-4 w-4 mr-1" />
						Clear
					</button>
				</div>
			</div>

			{#if error}
				<div class="text-destructive mb-4 flex-shrink-0">{error}</div>
			{/if}

			{#if loading}
				<div class="flex-1 flex items-center justify-center">
					<div class="text-center text-muted-foreground">Loading tracks...</div>
				</div>
			{:else if tracks.length === 0}
				<div class="flex-1 flex items-center justify-center">
					<div class="text-center text-muted-foreground">
						{#if searchQuery.trim() || selectedGenre || selectedArtist}
							No tracks found matching your filters
						{:else}
							No tracks in your library
						{/if}
					</div>
				</div>
			{:else}
				<div class="flex-1 flex flex-col min-h-0 overflow-hidden">
					<div class="flex-1 overflow-y-auto min-h-0">
						<Table class="border-2 border-white">
							<TableHeader>
								<TableRow>
									<TableHead class="w-12">
										<Checkbox
											checked={allSelected}
											onCheckedChange={() => toggleSelectAll()}
										/>
									</TableHead>
									<TableHead>Artist</TableHead>
									<TableHead>Track Name</TableHead>
									<TableHead>Album</TableHead>
									<TableHead>Genre</TableHead>
									<TableHead>Rating</TableHead>
									<TableHead>Favorite</TableHead>
									<TableHead>Play Count</TableHead>
									<TableHead>Skip Count</TableHead>
									<TableHead>Play Streak</TableHead>
									<TableHead class="w-24">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{#each tracks as track}
									<TableRow>
										<TableCell>
											<Checkbox
												checked={selectedTrackIds.has(track.id)}
												onCheckedChange={() => toggleTrackSelection(track.id)}
											/>
										</TableCell>
										<TableCell class="font-medium">{track.artist_name || '-'}</TableCell>
										<TableCell>{track.track_name}</TableCell>
										<TableCell class="text-muted-foreground">
											{track.album || '-'}
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.genre || '-'}
										</TableCell>
										<TableCell>
											<div class="flex items-center gap-1">
												{#each [1, 2, 3, 4, 5] as star}
													<button
														type="button"
														class="p-0 border-0 bg-transparent cursor-pointer hover:opacity-70"
														onclick={() => handleRatingChange(track.id, star)}
													>
														<Star
															class="h-4 w-4 {track.rating && track.rating >= star
																? 'fill-yellow-400 text-yellow-400'
																: 'text-muted-foreground'}"
														/>
													</button>
												{/each}
											</div>
										</TableCell>
										<TableCell>
											<button
												type="button"
												class="p-1 border-0 bg-transparent cursor-pointer hover:opacity-70"
												onclick={() => handleFavoriteToggle(track.id)}
											>
												<Heart
													class="h-5 w-5 {track.favorite
														? 'fill-red-500 text-red-500'
														: 'text-muted-foreground'}"
												/>
											</button>
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.playcount ?? 0}
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.skipcount ?? 0}
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.play_streak ?? 0}
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

					<!-- Pagination Controls -->
					<div class="flex items-center justify-between flex-shrink-0 pt-4 border-t border-border mt-4">
						<div class="text-sm text-muted-foreground">
							Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} tracks
						</div>
						<div class="flex items-center gap-2">
							<Button
								variant="outline"
								size="sm"
								onclick={previousPage}
								disabled={currentPage === 1 || loading}
							>
								<ChevronLeft class="h-4 w-4" />
								Previous
							</Button>
							<div class="text-sm">
								Page {currentPage} of {totalPages}
							</div>
							<Button
								variant="outline"
								size="sm"
								onclick={nextPage}
								disabled={currentPage === totalPages || loading}
							>
								Next
								<ChevronRight class="h-4 w-4" />
							</Button>
						</div>
					</div>
				</div>
			{/if}
		</CardContent>
	</Card>
</div>

<!-- Restore Dialog -->
{#if showRestoreDialog}
	<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onclick={closeRestoreDialog}>
		<div class="bg-background border-2 border-white rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col" onclick={(e) => e.stopPropagation()}>
			<CardHeader class="flex-shrink-0 pb-3">
				<div class="flex items-center justify-between">
					<CardTitle>Restore Tracks from All Tracks</CardTitle>
					<Button variant="ghost" size="sm" onclick={closeRestoreDialog}>
						<X class="h-4 w-4" />
					</Button>
				</div>
			</CardHeader>
			<CardContent class="flex-1 flex flex-col min-h-0 overflow-hidden">
				<!-- Search and Restore All -->
				<div class="mb-3 flex-shrink-0 space-y-3">
					<div class="flex gap-3 items-center">
						<div class="relative flex-1">
							<Search class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
							<input
								type="text"
								placeholder="Search removed tracks..."
								class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 pl-10"
								bind:value={removedTracksSearch}
								oninput={handleRemovedTracksSearchInput}
							/>
						</div>
						{#if removedTracksTotalCount > 0 && !removedTracksSearch.trim()}
							<Button
								onclick={handleRestoreAll}
								disabled={restoringAll}
							>
								<RotateCcw class="h-4 w-4 mr-2" />
								{restoringAll ? 'Restoring...' : `Restore All (${removedTracksTotalCount})`}
							</Button>
						{/if}
					</div>
				</div>

				{#if removedTracksLoading}
					<div class="flex-1 flex items-center justify-center">
						<div class="text-center text-muted-foreground">Loading removed tracks...</div>
					</div>
				{:else if removedTracks.length === 0}
					<div class="flex-1 flex items-center justify-center">
						<div class="text-center text-muted-foreground">
							{#if removedTracksSearch.trim()}
								No removed tracks found matching your search
							{:else}
								No removed tracks found
							{/if}
						</div>
					</div>
				{:else}
					<div class="flex-1 flex flex-col min-h-0 overflow-hidden">
						<div class="flex-1 overflow-y-auto min-h-0">
							<Table class="border-2 border-white">
								<TableHeader>
									<TableRow>
										<TableHead>Artist</TableHead>
										<TableHead>Track Name</TableHead>
										<TableHead>Album</TableHead>
										<TableHead>Genre</TableHead>
										<TableHead class="w-24">Actions</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{#each removedTracks as track}
										<TableRow>
											<TableCell class="font-medium">{track.artist_name || '-'}</TableCell>
											<TableCell>{track.track_name}</TableCell>
											<TableCell class="text-muted-foreground">
												{track.album || '-'}
											</TableCell>
											<TableCell class="text-muted-foreground">
												{track.genre || '-'}
											</TableCell>
											<TableCell>
												<Button
													variant="outline"
													size="sm"
													onclick={() => handleRestoreTrack(track.id)}
													disabled={restoringTrackId === track.id}
												>
													<RotateCcw class="h-4 w-4 mr-1" />
													Restore
												</Button>
											</TableCell>
										</TableRow>
									{/each}
								</TableBody>
							</Table>
						</div>

						<!-- Pagination -->
						{#if removedTracksTotalPages > 1}
							<div class="flex items-center justify-between flex-shrink-0 pt-4 border-t border-border mt-4">
								<div class="text-sm text-muted-foreground">
									Showing {((removedTracksPage - 1) * 50) + 1} to {Math.min(removedTracksPage * 50, removedTracksTotalCount)} of {removedTracksTotalCount} tracks
								</div>
								<div class="flex items-center gap-2">
									<Button
										variant="outline"
										size="sm"
										onclick={() => loadRemovedTracks(removedTracksPage - 1)}
										disabled={removedTracksPage === 1 || removedTracksLoading}
									>
										<ChevronLeft class="h-4 w-4" />
										Previous
									</Button>
									<div class="text-sm">
										Page {removedTracksPage} of {removedTracksTotalPages}
									</div>
									<Button
										variant="outline"
										size="sm"
										onclick={() => loadRemovedTracks(removedTracksPage + 1)}
										disabled={removedTracksPage === removedTracksTotalPages || removedTracksLoading}
									>
										Next
										<ChevronRight class="h-4 w-4" />
									</Button>
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</CardContent>
		</div>
	</div>
{/if}
