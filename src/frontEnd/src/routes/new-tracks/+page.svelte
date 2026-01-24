<script lang="ts">
	import { onMount } from 'svelte';
	import { getRecommendedTracks, getGenres, getArtists, loadArtistDiscography, downloadSelectedTracks } from '$lib/api/tracks';
	import type { RecommendedTrack, PaginatedResponse } from '$lib/schema';
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
	import Input from '$lib/components/ui/input.svelte';
	import Select from '$lib/components/ui/select.svelte';
	import Checkbox from '$lib/components/ui/checkbox.svelte';
	import { ChevronLeft, ChevronRight, Search, X } from 'lucide-svelte';

	let tracks = $state<RecommendedTrack[]>([]);
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
	let artistInput = $state('');
	let loadingArtist = $state(false);
	let selectedTrackIds = $state<Set<number>>(new Set());
	let downloadingTracks = $state(false);
	let artistStatus = $state<{
		show: boolean;
		message: string;
		artistName: string;
		tracksFound: number;
		newTracks: number;
		duplicates: number;
		updated: number;
		artistGenre: string | null;
		error: string | null;
	}>({
		show: false,
		message: '',
		artistName: '',
		tracksFound: 0,
		newTracks: 0,
		duplicates: 0,
		updated: 0,
		artistGenre: null,
		error: null
	});

	async function loadTracks(page: number = 1) {
		loading = true;
		error = null;

		try {
			const data: PaginatedResponse = await getRecommendedTracks(page, pageSize, {
				search: searchQuery.trim() || undefined,
				genre: selectedGenre || undefined,
				artistName: selectedArtist || undefined
			});
			tracks = data.tracks;
			currentPage = data.page;
			totalPages = data.total_pages;
			totalCount = data.count;
			// Clear selections when tracks change (new page or filter)
			selectedTrackIds = new Set();
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
				console.error('Error loading tracks:', err);
			} else if (err instanceof TypeError && err.message.includes('fetch')) {
				error = 'Network error: Unable to connect to API. Please check if the server is running.';
				console.error('Network error:', err);
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
			genres = await getGenres();
		} catch (err) {
			console.error('Error loading genres:', err);
		}
	}

	async function loadArtists() {
		try {
			artists = await getArtists();
		} catch (err) {
			console.error('Error loading artists:', err);
		}
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
		currentPage = 1; // Reset to first page on search
		loadTracks(1);
	}

	function handleGenreChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		selectedGenre = target.value;
		currentPage = 1; // Reset to first page on filter
		loadTracks(1);
	}

	function handleArtistChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		selectedArtist = target.value;
		currentPage = 1; // Reset to first page on filter
		loadTracks(1);
	}

	function clearFilters() {
		searchQuery = '';
		selectedGenre = '';
		selectedArtist = '';
		currentPage = 1;
		loadTracks(1);
	}

	function handleArtistInput(e: Event) {
		const target = e.target as HTMLInputElement;
		artistInput = target.value;
	}

	function toggleTrackSelection(trackId: number) {
		if (selectedTrackIds.has(trackId)) {
			selectedTrackIds.delete(trackId);
		} else {
			selectedTrackIds.add(trackId);
		}
		selectedTrackIds = new Set(selectedTrackIds); // Trigger reactivity
	}

	function toggleSelectAll() {
		if (selectedTrackIds.size === tracks.length) {
			selectedTrackIds = new Set();
		} else {
			selectedTrackIds = new Set(tracks.map(track => track.id));
		}
	}

	let allSelected = $derived(tracks.length > 0 && selectedTrackIds.size === tracks.length);

	async function handleDownloadSelected() {
		if (selectedTrackIds.size === 0) {
			return;
		}

		downloadingTracks = true;
		try {
			const trackIdsArray = Array.from(selectedTrackIds);
			const result = await downloadSelectedTracks(trackIdsArray);
			
			// Show success message
			alert(`Download complete: ${result.successful} successful, ${result.failed} failed`);
			
			// Clear selections
			selectedTrackIds = new Set();
			
			// Reload tracks to update the list (downloaded tracks will be filtered out)
			await loadTracks(currentPage);
		} catch (err) {
			console.error('Error downloading tracks:', err);
			alert(err instanceof Error ? err.message : 'Failed to download tracks');
		} finally {
			downloadingTracks = false;
		}
	}

	async function handleAddSongs() {
		console.log('handleAddSongs called, artistInput:', artistInput);
		const artistName = artistInput.trim();
		if (!artistName) {
			console.log('No artist name provided');
			return;
		}

		console.log('Starting to load discography for:', artistName);
		loadingArtist = true;
		artistStatus = {
			show: true,
			message: `Loading discography for "${artistName}"...`,
			artistName: artistName,
			tracksFound: 0,
			newTracks: 0,
			duplicates: 0,
			updated: 0,
			artistGenre: null,
			error: null
		};

		try {
			console.log('Calling loadArtistDiscography API...');
			const result = await loadArtistDiscography(artistName);
			console.log('API response:', result);
			artistStatus = {
				show: true,
				message: result.message || 'Discography loaded successfully',
				artistName: result.artist_name,
				tracksFound: result.tracks_found,
				newTracks: result.new_tracks,
				duplicates: result.duplicates,
				updated: result.updated || 0,
				artistGenre: result.artist_genre || null,
				error: null
			};

			// Clear the input
			artistInput = '';

			// Reload tracks to show the newly added ones
			await loadTracks(1);

			// Auto-hide after 5 seconds
			setTimeout(() => {
				artistStatus.show = false;
			}, 5000);
		} catch (err) {
			console.error('Error loading artist discography:', err);
			artistStatus = {
				show: true,
				message: 'Failed to load artist discography',
				artistName: artistName,
				tracksFound: 0,
				newTracks: 0,
				duplicates: 0,
				updated: 0,
				artistGenre: null,
				error: err instanceof Error ? err.message : 'Unknown error'
			};

			// Auto-hide after 5 seconds
			setTimeout(() => {
				artistStatus.show = false;
			}, 5000);
		} finally {
			loadingArtist = false;
		}
	}

	onMount(() => {
		loadGenres();
		loadArtists();
		loadTracks();
	});
</script>

<div class="flex flex-col h-[calc(100vh-80px)] overflow-hidden">
	<!-- Status Dialog -->
	{#if artistStatus.show}
		<div class="fixed top-20 right-6 z-50 max-w-md">
			<Card class="border-2 {artistStatus.error ? 'border-destructive' : 'border-green-500'}">
				<CardHeader class="pb-3">
					<CardTitle class="text-lg">
						{artistStatus.error ? 'Error' : 'Status'}
					</CardTitle>
				</CardHeader>
				<CardContent class="pt-0">
					<div class="space-y-2">
						<p class="text-sm font-medium">{artistStatus.message}</p>
						{#if artistStatus.error}
							<p class="text-sm text-destructive">{artistStatus.error}</p>
						{:else if !loadingArtist}
							<div class="text-sm text-muted-foreground space-y-1">
								<p>Artist: {artistStatus.artistName}</p>
								{#if artistStatus.artistGenre}
									<p>Artist genre: <span class="font-medium">{artistStatus.artistGenre}</span></p>
								{/if}
								<p>Tracks found: {artistStatus.tracksFound}</p>
								<p>New tracks added: {artistStatus.newTracks}</p>
								{#if artistStatus.updated > 0}
									<p>Tracks updated: {artistStatus.updated}</p>
								{/if}
								{#if artistStatus.duplicates > 0}
									<p>Duplicates skipped: {artistStatus.duplicates}</p>
								{/if}
							</div>
						{/if}
					</div>
				</CardContent>
			</Card>
		</div>
	{/if}

	<!-- Add Artists Card -->
	<Card class="mb-4 border-2 border-white flex-shrink-0">
		<CardHeader class="pb-3">
			<CardTitle>Add Artists</CardTitle>
		</CardHeader>
		<CardContent class="pt-0">
			<div class="flex gap-3 items-end">
				<div class="flex-1">
					<input
						type="text"
						placeholder="Enter artist name..."
						class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
						bind:value={artistInput}
						oninput={handleArtistInput}
					/>
				</div>
				<button
					type="button"
					class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90"
					onclick={() => {
						console.log('Button clicked! artistInput:', artistInput);
						handleAddSongs();
					}}
					disabled={!artistInput.trim() || loadingArtist}
				>
					{loadingArtist ? 'Loading...' : 'Add Songs'}
				</button>
			</div>
		</CardContent>
	</Card>

	<!-- Recommended Tracks Card -->
	<Card class="border-2 border-white flex-1 flex flex-col min-h-0 overflow-hidden">
		<CardHeader class="flex-shrink-0 pb-3">
			<CardTitle>Recommended Tracks</CardTitle>
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
				<!-- Download Selected Button -->
				<div class="flex justify-start">
					<Button
						onclick={handleDownloadSelected}
						disabled={selectedTrackIds.size === 0 || downloadingTracks}
					>
						{downloadingTracks ? 'Downloading...' : `Download Selected Songs (${selectedTrackIds.size})`}
					</Button>
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
							No recommended tracks found
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
										<TableCell class="font-medium">{track.artist_name}</TableCell>
										<TableCell>{track.track_name}</TableCell>
										<TableCell class="text-muted-foreground">
											{track.album || '-'}
										</TableCell>
										<TableCell class="text-muted-foreground">
											{track.genre || '-'}
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
