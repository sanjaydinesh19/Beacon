<script lang="ts">
	const projects = [
		{ name: 'AUV', desc: 'Autonomous Underwater Vehicle', status: 'active', href: '/projects/auv' },
		{ name: 'Quadruped', desc: 'Four-legged robot', status: 'active', href: '/projects/quadruped' },
		{ name: 'Code Pilot', desc: 'AI coding assistant', status: 'active', href: '/projects/code-pilot' },
		{ name: 'ROS2 Scaffolder', desc: 'ROS2 project generator', status: 'active', href: '/projects/ros2' },
		{ name: 'Resume Pipeline', desc: 'Automated resume builder', status: 'active', href: '/projects/resume' },
	];
</script>

<svelte:head>
	<title>Beacon</title>
</svelte:head>

<div class="page">
	<header>
		<h1>Welcome back</h1>
		<p class="subtitle">Your private lab. Build, test, reflect.</p>
	</header>

	<section>
		<h2 class="section-title">Quick Access</h2>
		<div class="quick-grid">
			<a href="/journal" class="quick-card journal">
				<span class="qc-icon">◎</span>
				<div>
					<div class="qc-name">Journal</div>
					<div class="qc-desc">Record today's entry</div>
				</div>
			</a>
			<a href="/github" class="quick-card activity">
				<span class="qc-icon">⊙</span>
				<div>
					<div class="qc-name">Activity</div>
					<div class="qc-desc">Latest commits & PRs</div>
				</div>
			</a>
			<a href="/placement" class="quick-card placements">
				<span class="qc-icon">◇</span>
				<div>
					<div class="qc-name">Placements</div>
					<div class="qc-desc">Company tracker</div>
				</div>
			</a>
		</div>
	</section>

	<section>
		<h2 class="section-title">Projects</h2>
		<div class="project-grid">
			{#each projects as p}
				<div class="project-card">
					<div class="project-header">
						<span class="project-name">{p.name}</span>
						<span class="status {p.status}">{p.status}</span>
					</div>
					<p class="project-desc">{p.desc}</p>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.page {
		max-width: 900px;
		display: flex;
		flex-direction: column;
		gap: 40px;
	}

	.page > * {
		animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.page > *:nth-child(1) { animation-delay: 0.08s; }
	.page > *:nth-child(2) { animation-delay: 0.16s; }
	.page > *:nth-child(3) { animation-delay: 0.24s; }

	header h1 {
		font-size: 28px;
		font-weight: 700;
		color: var(--text);
		margin-bottom: 6px;
	}

	.subtitle {
		color: var(--text-muted);
		font-size: 15px;
	}

	.section-title {
		font-size: 13px;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-muted);
		margin-bottom: 14px;
	}

	.quick-grid {
		display: flex;
		gap: 14px;
		flex-wrap: wrap;
	}

	.quick-card {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 16px 20px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		text-decoration: none;
		transition: all 0.15s;
		min-width: 200px;
	}

	.quick-card:hover {
		border-color: var(--accent);
		background: var(--accent-dim);
		text-decoration: none;
	}

	.quick-card.journal .qc-icon,
	.quick-card.activity .qc-icon,
	.quick-card.placements .qc-icon {
		font-size: 26px;
		color: var(--accent);
	}

	.qc-name {
		font-weight: 600;
		color: var(--text);
		font-size: 15px;
	}

	.qc-desc {
		font-size: 13px;
		color: var(--text-muted);
	}

	.project-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 14px;
	}

	.project-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 16px 18px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		transition: border-color 0.15s;
	}

	.project-card:hover {
		border-color: var(--border);
	}

	.project-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.project-name {
		font-weight: 600;
		font-size: 15px;
	}

	.status {
		font-size: 11px;
		font-weight: 500;
		padding: 2px 8px;
		border-radius: 100px;
		text-transform: capitalize;
	}

	.status.active {
		background: #5ce08a22;
		color: var(--green);
	}

	.project-desc {
		font-size: 13px;
		color: var(--text-muted);
	}
</style>
