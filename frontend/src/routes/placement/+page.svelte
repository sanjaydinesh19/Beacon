<script lang="ts">
	import { onMount } from 'svelte';

	type Company = {
		id: string;
		name: string;
		ctc: number | null;
		ctcLabel: string;
		roles: string[];
		location: string[];
		type: string;
		month: string;
		year: number;
		studentsPlaced: number | null;
		tier: 'super-dream' | 'dream' | 'normal';
		domain: string[];
		rounds: string[];
		eligibility: string;
		topics: string[];
		notes: string;
	};

	type TrackerEntry = {
		status: string;
		notes: string;
		links: string[];
		addedAt: string;
		updatedAt?: string;
	};

	const STATUSES = ['watchlist', 'researching', 'preparing', 'ready', 'applied', 'interviewed', 'offered', 'rejected'] as const;
	type Status = typeof STATUSES[number];

	const STATUS_LABELS: Record<string, string> = {
		watchlist: 'Watchlist',
		researching: 'Researching',
		preparing: 'Preparing',
		ready: 'Ready',
		applied: 'Applied',
		interviewed: 'Interviewed',
		offered: 'Offered',
		rejected: 'Rejected',
	};

	const TIER_ORDER: Record<string, number> = { 'super-dream': 0, dream: 1, normal: 2 };

	let companies: Company[] = [];
	let tracker: Record<string, TrackerEntry> = {};
	let lastBackup: string | null = null;
	let loading = true;
	let backingUp = false;
	let backupMsg = '';

	// Filters
	let search = '';
	let filterTier = '';
	let filterDomain = '';
	let filterType = '';

	// View
	let view: 'browse' | 'kanban' = 'browse';

	// Expanded company card
	let expanded: string | null = null;

	// Edit modal state
	let editId: string | null = null;
	let editStatus: Status = 'watchlist';
	let editNotes = '';

	async function loadAll() {
		loading = true;
		const [cRes, tRes] = await Promise.all([
			fetch('/api/placement/companies'),
			fetch('/api/placement/tracker'),
		]);
		const cData = await cRes.json();
		const tData = await tRes.json();
		companies = cData.companies.sort((a: Company, b: Company) => {
			const tierDiff = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
			if (tierDiff !== 0) return tierDiff;
			return (b.ctc ?? 0) - (a.ctc ?? 0);
		});
		tracker = tData.companies ?? {};
		lastBackup = tData.lastBackup;
		loading = false;
	}

	async function saveTracker(id: string, status: Status, notes: string) {
		const res = await fetch(`/api/placement/tracker/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ status, notes, links: tracker[id]?.links ?? [] }),
		});
		if (res.ok) {
			tracker[id] = await res.json();
			tracker = { ...tracker };
		}
		editId = null;
	}

	async function removeFromTracker(id: string) {
		await fetch(`/api/placement/tracker/${id}`, { method: 'DELETE' });
		const { [id]: _, ...rest } = tracker;
		tracker = rest;
	}

	async function backup() {
		backingUp = true;
		backupMsg = '';
		const res = await fetch('/api/placement/backup', { method: 'POST' });
		const data = await res.json();
		if (res.ok) {
			lastBackup = new Date().toISOString();
			backupMsg = `Backed up to ${data.repo}`;
		} else {
			backupMsg = data.detail ?? 'Backup failed';
		}
		backingUp = false;
	}

	function openEdit(id: string) {
		editId = id;
		editStatus = (tracker[id]?.status as Status) ?? 'watchlist';
		editNotes = tracker[id]?.notes ?? '';
	}

	onMount(loadAll);

	$: filtered = companies.filter(c => {
		if (filterTier && c.tier !== filterTier) return false;
		if (filterDomain && !c.domain.some(d => d.toLowerCase() === filterDomain.toLowerCase())) return false;
		if (filterType && c.type !== filterType) return false;
		if (search) {
			const q = search.toLowerCase();
			return c.name.toLowerCase().includes(q) || c.roles.some(r => r.toLowerCase().includes(q));
		}
		return true;
	});

	$: kanbanCols = STATUSES.map(s => ({
		status: s,
		label: STATUS_LABELS[s],
		items: Object.entries(tracker)
			.filter(([, v]) => v.status === s)
			.map(([id]) => companies.find(c => c.id === id))
			.filter(Boolean) as Company[],
	}));

	$: trackedIds = new Set(Object.keys(tracker));
	$: kanbanCount = Object.keys(tracker).length;

	function tierColor(tier: string) {
		if (tier === 'super-dream') return 'var(--accent)';
		if (tier === 'dream') return '#8b7cf8';
		return 'var(--text-muted)';
	}

	function tierLabel(tier: string) {
		if (tier === 'super-dream') return 'Super Dream';
		if (tier === 'dream') return 'Dream';
		return 'Normal';
	}

	function statusColor(s: string) {
		if (s === 'offered') return 'var(--green)';
		if (s === 'rejected') return 'var(--red)';
		if (s === 'applied' || s === 'interviewed') return '#8b7cf8';
		if (s === 'preparing' || s === 'ready') return 'var(--accent)';
		return 'var(--text-muted)';
	}

	function relativeTime(iso: string | null): string {
		if (!iso) return 'Never';
		const diff = Date.now() - new Date(iso).getTime();
		const m = Math.floor(diff / 60000);
		if (m < 1) return 'Just now';
		if (m < 60) return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24) return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}
</script>

<svelte:head><title>Placements · Beacon</title></svelte:head>

<!-- Edit Modal -->
{#if editId}
	{@const company = companies.find(c => c.id === editId)}
	<div class="modal-bg" on:click|self={() => editId = null}>
		<div class="modal">
			<div class="modal-header">
				<span class="modal-title">{company?.name}</span>
				<button class="modal-close" on:click={() => editId = null}>✕</button>
			</div>
			<div class="modal-body">
				<label class="field-label">Status</label>
				<div class="status-grid">
					{#each STATUSES as s}
						<button
							class="status-btn"
							class:active={editStatus === s}
							style="--sc: {statusColor(s)}"
							on:click={() => editStatus = s}
						>{STATUS_LABELS[s]}</button>
					{/each}
				</div>
				<label class="field-label">Notes</label>
				<textarea class="notes-input" bind:value={editNotes} placeholder="Your prep notes, round feedback, reminders..." rows={4}></textarea>
			</div>
			<div class="modal-footer">
				{#if trackedIds.has(editId)}
					<button class="btn-ghost" on:click={() => { removeFromTracker(editId!); editId = null; }}>Remove</button>
				{/if}
				<button class="btn-primary" on:click={() => saveTracker(editId!, editStatus, editNotes)}>Save</button>
			</div>
		</div>
	</div>
{/if}

<div class="page">
	<!-- Header -->
	<header>
		<div class="header-left">
			<h1>Placements</h1>
			<span class="sub">VIT Chennai · 2022–2025 data</span>
		</div>
		<div class="header-right">
			<span class="backup-time">Backup: {relativeTime(lastBackup)}</span>
			<button class="btn-ghost" on:click={backup} disabled={backingUp}>
				{backingUp ? 'Backing up...' : '↑ Backup'}
			</button>
		</div>
	</header>

	{#if backupMsg}
		<div class="backup-banner">{backupMsg}</div>
	{/if}

	<!-- Stats -->
	<div class="stats-row">
		<div class="stat"><span class="stat-val">{companies.length}</span><span class="stat-key">Companies</span></div>
		<div class="stat"><span class="stat-val">{companies.filter(c => c.tier === 'super-dream').length}</span><span class="stat-key">Super Dream</span></div>
		<div class="stat"><span class="stat-val">{companies.filter(c => c.tier === 'dream').length}</span><span class="stat-key">Dream</span></div>
		<div class="stat"><span class="stat-val">{kanbanCount}</span><span class="stat-key">Tracking</span></div>
		<div class="stat"><span class="stat-val">{Object.values(tracker).filter(t => t.status === 'offered').length}</span><span class="stat-key">Offers</span></div>
	</div>

	<!-- View Toggle + Filters -->
	<div class="controls">
		<div class="view-toggle">
			<button class="pill" class:active={view === 'browse'} on:click={() => view = 'browse'}>Browse</button>
			<button class="pill" class:active={view === 'kanban'} on:click={() => view = 'kanban'}>Tracker</button>
		</div>

		{#if view === 'browse'}
			<div class="filters">
				<input class="search-input" bind:value={search} placeholder="Search company or role..." />
				<select class="filter-select" bind:value={filterTier}>
					<option value="">All Tiers</option>
					<option value="super-dream">Super Dream (30+ LPA)</option>
					<option value="dream">Dream (15–30 LPA)</option>
					<option value="normal">Normal (&lt;15 LPA)</option>
				</select>
				<select class="filter-select" bind:value={filterDomain}>
					<option value="">All Domains</option>
					<option value="SDE">SDE</option>
					<option value="Data">Data / Analytics</option>
					<option value="AI/ML">AI / ML</option>
					<option value="Finance">Finance / Quant</option>
					<option value="Hardware">Hardware / VLSI</option>
					<option value="Consulting">Consulting</option>
					<option value="Non-Tech">Non-Tech</option>
				</select>
				<select class="filter-select" bind:value={filterType}>
					<option value="">All Types</option>
					<option value="FTE">FTE</option>
					<option value="PPO">PPO</option>
					<option value="Intern">Intern</option>
					<option value="FTE+Intern">FTE + Intern</option>
				</select>
			</div>
		{/if}
	</div>

	<!-- Browse View -->
	{#if view === 'browse'}
		{#if loading}
			<div class="card-grid">
				{#each Array(12) as _}
					<div class="skeleton-card"></div>
				{/each}
			</div>
		{:else if filtered.length === 0}
			<div class="empty-state"><span>◎</span><p>No companies match your filters.</p></div>
		{:else}
			<div class="card-grid">
				{#each filtered as c}
					<div class="company-card" class:tracked={trackedIds.has(c.id)}>
						<div class="card-top">
							<div class="card-name-row">
								<span class="card-name">{c.name}</span>
								{#if trackedIds.has(c.id)}
									<span class="tracked-dot" style="background: {statusColor(tracker[c.id].status)}" title={STATUS_LABELS[tracker[c.id].status]}></span>
								{/if}
							</div>
							<span class="tier-badge" style="color: {tierColor(c.tier)}; border-color: {tierColor(c.tier)}40">{tierLabel(c.tier)}</span>
						</div>

						<div class="ctc-row">
							<span class="ctc">{c.ctcLabel}</span>
							<span class="card-type">{c.type}</span>
						</div>

						<div class="card-roles">
							{#each c.roles.slice(0, 2) as r}
								<span class="role-chip">{r}</span>
							{/each}
						</div>

						<div class="card-meta">
							<span>📍 {c.location.slice(0, 2).join(', ')}{c.location.length > 2 ? ' +more' : ''}</span>
							<span>{c.month} {c.year}</span>
						</div>

						{#if expanded === c.id}
							<div class="card-expanded">
								{#if c.domain.length}
									<div class="expand-row">
										<span class="expand-label">Domain</span>
										<div class="tag-row">{#each c.domain as d}<span class="tag">{d}</span>{/each}</div>
									</div>
								{/if}
								{#if c.eligibility}
									<div class="expand-row">
										<span class="expand-label">Eligibility</span>
										<span class="expand-val">{c.eligibility}</span>
									</div>
								{/if}
								{#if c.rounds.length}
									<div class="expand-row col">
										<span class="expand-label">Interview Rounds</span>
										<ol class="rounds-list">
											{#each c.rounds as r}<li>{r}</li>{/each}
										</ol>
									</div>
								{/if}
								{#if c.topics.length}
									<div class="expand-row">
										<span class="expand-label">Topics</span>
										<div class="tag-row">{#each c.topics as t}<span class="tag topic">{t}</span>{/each}</div>
									</div>
								{/if}
								{#if c.notes}
									<div class="expand-row col">
										<span class="expand-label">Notes</span>
										<span class="expand-note">{c.notes}</span>
									</div>
								{/if}
								{#if trackedIds.has(c.id) && tracker[c.id].notes}
									<div class="expand-row col">
										<span class="expand-label">My Notes</span>
										<span class="expand-note my-note">{tracker[c.id].notes}</span>
									</div>
								{/if}
							</div>
						{/if}

						<div class="card-actions">
							<button class="action-link" on:click={() => expanded = expanded === c.id ? null : c.id}>
								{expanded === c.id ? 'Less ↑' : 'Details ↓'}
							</button>
							<button class="action-track" on:click={() => openEdit(c.id)}>
								{trackedIds.has(c.id) ? `${STATUS_LABELS[tracker[c.id].status]} ✎` : '+ Track'}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

	<!-- Kanban View -->
	{:else}
		{#if kanbanCount === 0}
			<div class="empty-state">
				<span>◎</span>
				<p>No companies tracked yet. Go to Browse and click "+ Track" on a company.</p>
			</div>
		{:else}
			<div class="kanban">
				{#each kanbanCols.filter(col => col.items.length > 0 || ['watchlist','preparing','applied'].includes(col.status)) as col}
					<div class="kanban-col">
						<div class="col-header">
							<span class="col-title" style="color: {statusColor(col.status)}">{col.label}</span>
							<span class="col-count">{col.items.length}</span>
						</div>
						{#each col.items as c}
							<div class="kanban-card">
								<div class="kc-top">
									<span class="kc-name">{c.name}</span>
									<span class="tier-dot" style="background: {tierColor(c.tier)}" title={tierLabel(c.tier)}></span>
								</div>
								<span class="kc-ctc">{c.ctcLabel}</span>
								{#if tracker[c.id]?.notes}
									<p class="kc-notes">{tracker[c.id].notes}</p>
								{/if}
								<button class="action-track small" on:click={() => openEdit(c.id)}>Edit ✎</button>
							</div>
						{/each}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.page {
		max-width: 1100px;
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		animation: fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.header-left { display: flex; align-items: baseline; gap: 12px; }

	header h1 { font-size: 26px; font-weight: 700; color: var(--text); }

	.sub { font-size: 13px; color: var(--text-muted); }

	.header-right { display: flex; align-items: center; gap: 10px; }

	.backup-time { font-size: 12px; color: var(--text-muted); }

	.backup-banner {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 10px 16px;
		font-size: 13px;
		color: var(--green);
		animation: fadeUp 0.3s both;
	}

	/* Stats */
	.stats-row {
		display: flex;
		gap: 12px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both;
	}

	.stat {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 12px 20px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		flex: 1;
	}

	.stat-val { font-size: 22px; font-weight: 700; color: var(--text); }
	.stat-key { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

	/* Controls */
	.controls {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.08s both;
	}

	.view-toggle { display: flex; gap: 4px; }

	.filters { display: flex; gap: 8px; flex-wrap: wrap; flex: 1; }

	.search-input {
		flex: 1;
		min-width: 180px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 7px 12px;
		color: var(--text);
		font-size: 13px;
		outline: none;
		transition: border-color 0.15s;
	}
	.search-input:focus { border-color: var(--accent); }

	.filter-select {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 7px 10px;
		color: var(--text);
		font-size: 13px;
		outline: none;
		cursor: pointer;
	}

	/* Pills */
	.pill {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-muted);
		border-radius: 100px;
		padding: 5px 14px;
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.pill:hover { border-color: var(--text-muted); color: var(--text); }
	.pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

	/* Buttons */
	.btn-ghost {
		background: var(--surface);
		border: 1px solid var(--border);
		color: var(--text-muted);
		border-radius: 8px;
		padding: 6px 14px;
		font-size: 13px;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn-ghost:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
	.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

	.btn-primary {
		background: var(--accent);
		border: none;
		color: #000;
		border-radius: 8px;
		padding: 7px 18px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.btn-primary:hover { opacity: 0.85; }

	/* Card Grid */
	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 12px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
	}

	.company-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		transition: border-color 0.15s;
	}
	.company-card:hover { border-color: var(--border); }
	.company-card.tracked { border-color: var(--accent)30; }

	.card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }

	.card-name-row { display: flex; align-items: center; gap: 8px; }

	.card-name { font-size: 15px; font-weight: 600; color: var(--text); }

	.tracked-dot {
		width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
	}

	.tier-badge {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		border: 1px solid;
		border-radius: 100px;
		padding: 2px 8px;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.ctc-row { display: flex; align-items: baseline; justify-content: space-between; }
	.ctc { font-size: 17px; font-weight: 700; color: var(--text); }
	.card-type { font-size: 11px; color: var(--text-muted); }

	.card-roles { display: flex; flex-wrap: wrap; gap: 4px; }
	.role-chip {
		font-size: 11px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 2px 8px;
		color: var(--text-muted);
	}

	.card-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); }

	/* Expanded */
	.card-expanded {
		border-top: 1px solid var(--border);
		padding-top: 10px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.expand-row { display: flex; gap: 10px; align-items: flex-start; }
	.expand-row.col { flex-direction: column; gap: 4px; }
	.expand-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; flex-shrink: 0; min-width: 80px; }
	.expand-val { font-size: 12px; color: var(--text); }
	.expand-note { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
	.my-note { color: var(--accent); }

	.tag-row { display: flex; flex-wrap: wrap; gap: 4px; }
	.tag {
		font-size: 11px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 2px 7px;
		color: var(--text-muted);
	}
	.tag.topic { border-color: var(--accent)40; color: var(--accent); background: var(--accent-dim); }

	.rounds-list { font-size: 12px; color: var(--text); padding-left: 16px; display: flex; flex-direction: column; gap: 3px; }
	.rounds-list li { color: var(--text-muted); }

	/* Card Actions */
	.card-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 2px; }

	.action-link {
		background: none; border: none; color: var(--text-muted);
		font-size: 12px; cursor: pointer; padding: 0;
		transition: color 0.15s;
	}
	.action-link:hover { color: var(--text); }

	.action-track {
		background: var(--accent-dim);
		border: 1px solid var(--accent)60;
		color: var(--accent);
		border-radius: 6px;
		padding: 4px 12px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.action-track:hover { background: var(--accent); color: #000; }
	.action-track.small { padding: 3px 10px; font-size: 11px; }

	/* Skeleton */
	.skeleton-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		height: 160px;
		animation: shimmer 1.6s ease-in-out infinite;
	}
	@keyframes shimmer { 0%,100%{opacity:.4} 50%{opacity:.7} }

	/* Kanban */
	.kanban {
		display: flex;
		gap: 12px;
		overflow-x: auto;
		padding-bottom: 8px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
	}

	.kanban-col {
		flex-shrink: 0;
		width: 220px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.col-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 4px;
		border-bottom: 1px solid var(--border);
	}

	.col-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; }
	.col-count { font-size: 12px; color: var(--text-muted); background: var(--surface-2); border-radius: 100px; padding: 1px 8px; }

	.kanban-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.kc-top { display: flex; align-items: center; justify-content: space-between; }
	.kc-name { font-size: 14px; font-weight: 600; color: var(--text); }
	.tier-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
	.kc-ctc { font-size: 12px; font-weight: 600; color: var(--accent); }
	.kc-notes { font-size: 11px; color: var(--text-muted); line-height: 1.4; }

	/* Modal */
	.modal-bg {
		position: fixed; inset: 0;
		background: rgba(0,0,0,0.6);
		backdrop-filter: blur(4px);
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		animation: fadeUp 0.2s both;
	}

	.modal {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 14px;
		width: 480px;
		max-width: calc(100vw - 32px);
		box-shadow: 0 24px 64px rgba(0,0,0,0.5);
		overflow: hidden;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 18px 20px;
		border-bottom: 1px solid var(--border);
	}

	.modal-title { font-size: 16px; font-weight: 600; color: var(--text); }
	.modal-close { background: none; border: none; color: var(--text-muted); font-size: 16px; cursor: pointer; padding: 0; }

	.modal-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; }

	.field-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }

	.status-grid { display: flex; flex-wrap: wrap; gap: 6px; }

	.status-btn {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-muted);
		border-radius: 6px;
		padding: 5px 12px;
		font-size: 12px;
		cursor: pointer;
		transition: all 0.15s;
	}
	.status-btn:hover { border-color: var(--sc); color: var(--sc); }
	.status-btn.active { background: color-mix(in srgb, var(--sc) 15%, transparent); border-color: var(--sc); color: var(--sc); }

	.notes-input {
		width: 100%;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px 12px;
		color: var(--text);
		font-size: 13px;
		resize: vertical;
		outline: none;
		transition: border-color 0.15s;
	}
	.notes-input:focus { border-color: var(--accent); }

	.modal-footer {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
		padding: 14px 20px;
		border-top: 1px solid var(--border);
	}

	/* Empty */
	.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 0; color: var(--text-muted); }
	.empty-state span { font-size: 28px; opacity: 0.4; }
</style>
