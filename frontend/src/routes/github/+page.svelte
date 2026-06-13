<script lang="ts">
	import { onMount } from 'svelte';

	type Item = {
		type: 'commit' | 'pr';
		repo: string;
		repoFull: string;
		title: string;
		url: string;
		time: string;
		meta: string;
		number: number | null;
	};

	let username = '';
	let items: Item[] = [];
	let loading = true;
	let error = '';

	async function load() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/github/activity');
			const data = await res.json();
			if (!res.ok) throw new Error(data.detail ?? 'Failed to load');
			username = data.username;
			items = data.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	function accentFor(item: Item): string {
		if (item.type === 'commit') return 'var(--accent)';
		if (item.meta === 'merged') return 'var(--green)';
		if (item.meta === 'closed') return 'var(--text-muted)';
		return '#8b7cf8';
	}

	function labelFor(item: Item): string {
		if (item.type === 'commit') return 'pushed';
		if (item.meta === 'merged') return 'merged pr';
		if (item.meta === 'closed') return 'closed pr';
		return 'opened pr';
	}
</script>

<svelte:head><title>Activity · Beacon</title></svelte:head>

<div class="page">
	<header>
		<div class="header-left">
			<h1>Activity</h1>
			{#if username && !loading}
				<a
					class="handle"
					href="https://github.com/{username}"
					target="_blank"
					rel="noopener"
				>@{username}</a>
			{/if}
		</div>
		<button class="refresh-btn" on:click={load} disabled={loading} title="Refresh">
			<span class="refresh-icon" class:spin={loading}>↻</span>
		</button>
	</header>

	{#if loading}
		<div class="feed">
			{#each Array(10) as _, i}
				<div class="skeleton" style="animation-delay: {i * 0.04}s">
					<div class="sk-bar"></div>
					<div class="sk-body">
						<div class="sk-top">
							<div class="sk-line" style="width: 80px"></div>
							<div class="sk-line" style="width: 50px"></div>
						</div>
						<div class="sk-line" style="width: {60 + Math.random() * 30}%"></div>
						<div class="sk-line" style="width: 60px; margin-top: 2px"></div>
					</div>
				</div>
			{/each}
		</div>

	{:else if error}
		<div class="empty-state">
			<span class="empty-icon">⚠</span>
			<p>{error}</p>
		</div>

	{:else if items.length === 0}
		<div class="empty-state">
			<span class="empty-icon">◎</span>
			<p>No recent activity found.</p>
		</div>

	{:else}
		<div class="feed">
			{#each items as item, i}
				<a
					class="feed-item"
					href={item.url}
					target="_blank"
					rel="noopener"
					style="--c: {accentFor(item)}; animation-delay: {i * 0.035}s"
				>
					<div class="item-bar"></div>
					<div class="item-body">
						<div class="item-top">
							<div class="item-left">
								<span class="repo-name">{item.repo}</span>
								<span class="event-label" style="color: var(--c)">{labelFor(item)}</span>
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
</div>

<style>
	.page {
		max-width: 720px;
		display: flex;
		flex-direction: column;
		gap: 28px;
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

	.refresh-icon {
		display: inline-block;
		transition: transform 0.3s;
	}

	.refresh-icon.spin {
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* ── Feed ─────────────────────────────────────────────────────────────── */

	.feed {
		display: flex;
		flex-direction: column;
		gap: 8px;
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.06s both;
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

	.feed-item:hover .arrow {
		opacity: 1;
	}

	.item-bar {
		width: 3px;
		flex-shrink: 0;
		background: var(--c);
		border-radius: 3px 0 0 3px;
		opacity: 0.85;
	}

	.item-body {
		flex: 1;
		padding: 13px 16px;
		display: flex;
		flex-direction: column;
		gap: 5px;
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
		font-weight: 450;
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
		font-size: 14px;
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

	.sk-bar {
		width: 3px;
		background: var(--border);
	}

	.sk-body {
		flex: 1;
		padding: 13px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.sk-top {
		display: flex;
		gap: 10px;
	}

	.sk-line {
		height: 12px;
		border-radius: 4px;
		background: var(--surface-2);
		animation: shimmer 1.6s ease-in-out infinite;
	}

	@keyframes shimmer {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 0.8; }
	}

	/* ── Empty / Error ────────────────────────────────────────────────────── */

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 60px 0;
		color: var(--text-muted);
	}

	.empty-icon {
		font-size: 32px;
		opacity: 0.5;
	}
</style>
