<script lang="ts">
	import { onMount } from 'svelte';
	import ContributionChart from '$lib/ContributionChart.svelte';

	type Week = { date: string; count: number; level: number }[];

	type ActivityItem = {
		type: 'commit' | 'pr';
		repo: string;
		repoFull: string;
		title: string;
		url: string;
		time: string;
		meta: string;
		number: number | null;
	};

	// GitHub contributions
	let ghWeeks: Week[] = [];
	let ghTotal = 0;
	let ghUsername = '';
	let ghLoading = true;
	let ghError = '';

	// LeetCode contributions
	let lcWeeks: Week[] = [];
	let lcTotal = 0;
	let lcStreak = 0;
	let lcLoading = true;
	let lcError = '';

	// Activity feed
	let activityItems: ActivityItem[] = [];
	let activityLoading = true;
	let activityError = '';

	async function loadContributions() {
		ghLoading = true; lcLoading = true;
		ghError = ''; lcError = '';

		const [ghRes, lcRes] = await Promise.allSettled([
			fetch('/api/github/contributions'),
			fetch('/api/github/leetcode'),
		]);

		if (ghRes.status === 'fulfilled') {
			const d = await ghRes.value.json();
			if (!ghRes.value.ok) ghError = d.detail ?? 'Failed';
			else { ghWeeks = d.weeks; ghTotal = d.total; ghUsername = d.username; }
		} else {
			ghError = 'Network error';
		}

		if (lcRes.status === 'fulfilled') {
			const d = await lcRes.value.json();
			if (!lcRes.value.ok) lcError = d.detail ?? 'Failed';
			else { lcWeeks = d.weeks; lcTotal = d.total; lcStreak = d.streak; }
		} else {
			lcError = 'Network error';
		}

		ghLoading = false; lcLoading = false;
	}

	async function loadActivity() {
		activityLoading = true;
		activityError = '';
		try {
			const res = await fetch('/api/github/activity');
			const data = await res.json();
			if (!res.ok) throw new Error(data.detail ?? 'Failed to load');
			activityItems = data.items;
		} catch (e) {
			activityError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			activityLoading = false;
		}
	}

	onMount(() => {
		loadContributions();
		loadActivity();
	});

	function accentFor(item: ActivityItem): string {
		if (item.type === 'commit') return 'var(--accent)';
		if (item.meta === 'merged') return 'var(--green)';
		if (item.meta === 'closed') return 'var(--text-muted)';
		return '#8b7cf8';
	}

	function labelFor(item: ActivityItem): string {
		if (item.type === 'commit') return 'pushed';
		if (item.meta === 'merged') return 'merged pr';
		if (item.meta === 'closed') return 'closed pr';
		return 'opened pr';
	}
</script>

<svelte:head><title>Activity · Beacon</title></svelte:head>

<div class="page">

	<!-- ── Header ────────────────────────────────────────────────────────── -->
	<header>
		<div class="header-left">
			<h1>Activity</h1>
			{#if ghUsername && !ghLoading}
				<a class="handle" href="https://github.com/{ghUsername}" target="_blank" rel="noopener">
					@{ghUsername}
				</a>
			{/if}
		</div>
		<button
			class="refresh-btn"
			on:click={() => { loadContributions(); loadActivity(); }}
			disabled={ghLoading || lcLoading || activityLoading}
			title="Refresh"
		>
			<span class="refresh-icon" class:spin={ghLoading || lcLoading || activityLoading}>↻</span>
		</button>
	</header>

	<!-- ── Contribution Charts ───────────────────────────────────────────── -->
	<section class="charts">
		<ContributionChart
			weeks={ghWeeks}
			total={ghTotal}
			label="GitHub"
			baseColor="#f5a623"
			loading={ghLoading}
			error={ghError}
		/>
		<ContributionChart
			weeks={lcWeeks}
			total={lcTotal}
			label="LeetCode"
			baseColor="#5ce08a"
			loading={lcLoading}
			error={lcError}
		/>
		{#if lcStreak > 0}
			<div class="lc-stats">
				<span class="stat-pill">🔥 {lcStreak} day streak</span>
			</div>
		{/if}
	</section>

	<!-- ── Activity Feed ─────────────────────────────────────────────────── -->
	<section class="feed-section">
		<h2 class="section-title">Recent Events</h2>

		{#if activityLoading}
			<div class="feed">
				{#each Array(10) as _, i}
					<div class="skeleton" style="animation-delay: {i * 0.04}s">
						<div class="sk-bar"></div>
						<div class="sk-body">
							<div class="sk-top">
								<div class="sk-line" style="width: 80px"></div>
								<div class="sk-line" style="width: 50px"></div>
							</div>
							<div class="sk-line" style="width: {55 + (i * 7) % 30}%"></div>
							<div class="sk-line short"></div>
						</div>
					</div>
				{/each}
			</div>

		{:else if activityError}
			<div class="empty-state">
				<span class="empty-icon">⚠</span>
				<p>{activityError}</p>
			</div>

		{:else if activityItems.length === 0}
			<div class="empty-state">
				<span class="empty-icon">◎</span>
				<p>No recent activity found.</p>
			</div>

		{:else}
			<div class="feed">
				{#each activityItems as item, i}
					<a
						class="feed-item"
						href={item.url}
						target="_blank"
						rel="noopener noreferrer"
						style="--c: {accentFor(item)}; animation-delay: {i * 0.03}s"
					>
						<div class="item-bar"></div>
						<div class="item-body">
							<div class="item-top">
								<div class="item-left">
									<span class="repo-name">{item.repo}</span>
									<span class="event-label" style="color: {accentFor(item)}">{labelFor(item)}</span>
								</div>
								<span class="item-time">{item.time}</span>
							</div>
							<p class="item-title">{item.title}</p>
							<div class="item-foot">
								{#if item.type === 'commit'}
									<code class="sha">{item.meta}</code>
								{:else if item.number}
									<code class="sha">#{item.number}</code>
								{/if}
							</div>
						</div>
						<span class="arrow" aria-hidden="true">↗</span>
					</a>
				{/each}
			</div>
		{/if}
	</section>
</div>

<style>
	.page {
		max-width: 780px;
		display: flex;
		flex-direction: column;
		gap: 36px;
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		animation: fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.header-left {
		display: flex;
		align-items: baseline;
		gap: 12px;
	}

	header h1 {
		font-size: 26px;
		font-weight: 700;
		color: var(--text);
	}

	.handle {
		font-size: 14px;
		color: var(--text-muted);
		font-weight: 500;
		text-decoration: none;
		transition: color 0.15s;
	}

	.handle:hover {
		color: var(--accent);
		text-decoration: none;
	}

	.refresh-btn {
		background: var(--surface);
		border: 1px solid var(--border);
		color: var(--text-muted);
		border-radius: 8px;
		padding: 6px 12px;
		font-size: 18px;
		line-height: 1;
		cursor: pointer;
		transition: all 0.15s;
	}

	.refresh-btn:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--accent);
	}

	.refresh-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.refresh-icon { display: inline-block; }
	.refresh-icon.spin { animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Charts ───────────────────────────────────────────────────────────── */

	.charts {
		display: flex;
		flex-direction: column;
		gap: 12px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both;
	}

	.lc-stats {
		display: flex;
		gap: 10px;
	}

	.stat-pill {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-muted);
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 100px;
		padding: 3px 12px;
	}

	/* ── Section ──────────────────────────────────────────────────────────── */

	.feed-section {
		display: flex;
		flex-direction: column;
		gap: 14px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
	}

	.section-title {
		font-size: 13px;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	/* ── Feed ─────────────────────────────────────────────────────────────── */

	.feed {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.feed-item {
		position: relative;
		display: flex;
		align-items: stretch;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		text-decoration: none;
		overflow: hidden;
		transition: border-color 0.15s, background 0.15s;
		animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.feed-item:hover {
		border-color: var(--c);
		background: var(--surface-2);
		text-decoration: none;
	}

	.feed-item:hover .arrow { opacity: 1; }

	.item-bar {
		width: 3px;
		flex-shrink: 0;
		background: var(--c);
		opacity: 0.85;
	}

	.item-body {
		flex: 1;
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
	}

	.item-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	.item-left {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}

	.repo-name {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.event-label {
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		white-space: nowrap;
		opacity: 0.9;
	}

	.item-time {
		font-size: 12px;
		color: var(--text-muted);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.item-title {
		font-size: 14px;
		color: var(--text);
		line-height: 1.4;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.item-foot {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.sha {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		background: var(--surface-2);
		border: 1px solid var(--border);
		padding: 1px 6px;
		border-radius: 4px;
	}

	.arrow {
		position: absolute;
		top: 12px;
		right: 14px;
		font-size: 13px;
		color: var(--text-muted);
		opacity: 0;
		transition: opacity 0.15s;
	}

	/* ── Skeleton ─────────────────────────────────────────────────────────── */

	.skeleton {
		display: flex;
		align-items: stretch;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.sk-bar { width: 3px; background: var(--border); }

	.sk-body {
		flex: 1;
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.sk-top { display: flex; gap: 10px; }

	.sk-line {
		height: 11px;
		border-radius: 4px;
		background: var(--surface-2);
		animation: shimmer 1.6s ease-in-out infinite;
	}

	.sk-line.short { width: 55px; }

	@keyframes shimmer {
		0%, 100% { opacity: 0.35; }
		50% { opacity: 0.75; }
	}

	/* ── Empty / Error ────────────────────────────────────────────────────── */

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 48px 0;
		color: var(--text-muted);
	}

	.empty-icon { font-size: 28px; opacity: 0.5; }
</style>
