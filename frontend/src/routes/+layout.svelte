<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';

	const nav = [
		{ href: '/', label: 'Dashboard', icon: '⬡' },
		{ href: '/journal', label: 'Journal', icon: '◎' },
		{ href: '/github', label: 'Activity', icon: '⊙' },
		{ href: '/placement', label: 'Placements', icon: '◇' },
	];
</script>

<div class="shell">
	<div class="glow-orb" aria-hidden="true"></div>
	<aside class="sidebar">
		<div class="logo">
			<span class="beacon-icon">◈</span>
			<span class="beacon-name">Beacon</span>
		</div>
		<nav>
			{#each nav as { href, label, icon }}
				<a {href} class:active={$page.url.pathname === href}>
					<span class="nav-icon">{icon}</span>
					{label}
				</a>
			{/each}
		</nav>
		<div class="sidebar-footer">
			<span class="version">v0.1</span>
		</div>
	</aside>

	<main class="content">
		<slot />
	</main>
</div>

<style>
	.shell {
		display: flex;
		height: 100vh;
		overflow: hidden;
	}

	.sidebar {
		width: 200px;
		flex-shrink: 0;
		background: var(--surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		padding: 20px 12px;
		gap: 6px;
		animation: slideInLeft 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
		position: relative;
		z-index: 1;
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 4px 12px 20px;
		border-bottom: 1px solid var(--border);
		margin-bottom: 8px;
	}

	.beacon-icon {
		font-size: 22px;
		color: var(--accent);
		filter: drop-shadow(0 0 6px var(--accent));
	}

	.beacon-name {
		font-size: 17px;
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--text);
	}

	nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
	}

	nav a {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 12px;
		border-radius: var(--radius);
		color: var(--text-muted);
		font-size: 14px;
		font-weight: 500;
		transition: all 0.15s;
		text-decoration: none;
	}

	nav a:hover {
		background: var(--surface-2);
		color: var(--text);
		text-decoration: none;
	}

	nav a.active {
		background: var(--accent-dim);
		color: var(--accent);
	}

	.nav-icon {
		font-size: 16px;
		width: 18px;
		text-align: center;
	}

	.sidebar-footer {
		padding-top: 12px;
		border-top: 1px solid var(--border);
	}

	.version {
		font-size: 12px;
		color: var(--text-muted);
		padding: 0 12px;
	}

	.content {
		flex: 1;
		overflow-y: auto;
		padding: 32px 40px;
		position: relative;
		z-index: 1;
	}

	@media (max-width: 640px) {
		.sidebar {
			width: 60px;
		}
		.beacon-name,
		nav a span:last-child,
		.version {
			display: none;
		}
		nav a {
			justify-content: center;
		}
	}
</style>
