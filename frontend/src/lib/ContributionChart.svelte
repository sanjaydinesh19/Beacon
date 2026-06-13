<script lang="ts">
	export let weeks: { date: string; count: number; level: number }[][] = [];
	export let total: number = 0;
	export let label: string = '';
	export let baseColor: string = '#f5a623';
	export let loading: boolean = false;
	export let error: string = '';

	const CELL = 11;
	const GAP = 2;
	const STEP = CELL + GAP;
	const MONTH_H = 18;
	const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

	// 8-digit hex: baseColor + alpha suffix
	function cellColor(level: number): string {
		if (level === 0) return '#1a1a28';
		const alphas = ['', '40', '73', 'b3', 'ff'];
		return `${baseColor}${alphas[level]}`;
	}

	function monthLabels(): { x: number; text: string }[] {
		const labels: { x: number; text: string }[] = [];
		let prev = -1;
		weeks.forEach((week, wi) => {
			if (!week[0]) return;
			const m = new Date(week[0].date + 'T00:00:00').getMonth();
			if (m !== prev) {
				labels.push({ x: wi * STEP, text: MONTHS[m] });
				prev = m;
			}
		});
		return labels;
	}

	$: svgW = weeks.length * STEP;
	$: svgH = MONTH_H + 7 * STEP;
	$: mlabels = weeks.length ? monthLabels() : [];

	let tip = { visible: false, x: 0, y: 0, date: '', count: 0 };

	function onEnter(e: MouseEvent, day: { date: string; count: number }) {
		tip = { visible: true, x: e.clientX, y: e.clientY, date: day.date, count: day.count };
	}
	function onLeave() { tip = { ...tip, visible: false }; }

	const LEGEND_LEVELS = [0, 1, 2, 3, 4];
</script>

<div class="chart-wrap">
	<div class="chart-header">
		<span class="chart-label">{label}</span>
		{#if !loading && !error}
			<span class="chart-total">{total.toLocaleString()} contributions this year</span>
		{/if}
	</div>

	{#if loading}
		<div class="chart-skeleton">
			{#each Array(7) as _}
				<div class="sk-row">
					{#each Array(53) as _}
						<div class="sk-cell"></div>
					{/each}
				</div>
			{/each}
		</div>

	{:else if error}
		<div class="chart-error">{error}</div>

	{:else}
		<div class="chart-scroll">
			<svg width={svgW} height={svgH} class="contrib-svg">
				{#each mlabels as ml}
					<text
						x={ml.x}
						y={MONTH_H - 5}
						class="month-lbl"
					>{ml.text}</text>
				{/each}

				{#each weeks as week, wi}
					{#each week as day, di}
						<rect
							x={wi * STEP}
							y={MONTH_H + di * STEP}
							width={CELL}
							height={CELL}
							rx={2}
							fill={cellColor(day.level)}
							class="cell"
							on:mouseenter={(e) => onEnter(e, day)}
							on:mouseleave={onLeave}
						/>
					{/each}
				{/each}
			</svg>
		</div>

		<div class="legend">
			<span class="legend-text">Less</span>
			{#each LEGEND_LEVELS as lv}
				<span class="legend-cell" style="background: {cellColor(lv)}"></span>
			{/each}
			<span class="legend-text">More</span>
		</div>
	{/if}
</div>

{#if tip.visible}
	<div class="tooltip" style="left: {tip.x + 12}px; top: {tip.y - 36}px">
		<strong>{tip.count}</strong> on {tip.date}
	</div>
{/if}

<style>
	.chart-wrap {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 18px 20px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.chart-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
	}

	.chart-label {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		color: var(--text-muted);
	}

	.chart-total {
		font-size: 12px;
		color: var(--text-muted);
	}

	.chart-scroll {
		overflow-x: auto;
		overflow-y: hidden;
	}

	.contrib-svg {
		display: block;
	}

	.month-lbl {
		font-size: 10px;
		fill: var(--text-muted);
		font-family: var(--font);
	}

	.cell {
		cursor: crosshair;
		transition: opacity 0.1s;
	}

	.cell:hover {
		opacity: 0.75;
	}

	/* Legend */
	.legend {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.legend-text {
		font-size: 11px;
		color: var(--text-muted);
	}

	.legend-cell {
		width: 11px;
		height: 11px;
		border-radius: 2px;
		flex-shrink: 0;
	}

	/* Skeleton */
	.chart-skeleton {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.sk-row {
		display: flex;
		gap: 2px;
	}

	.sk-cell {
		width: 11px;
		height: 11px;
		border-radius: 2px;
		background: var(--surface-2);
		animation: shimmer 1.6s ease-in-out infinite;
	}

	.sk-cell:nth-child(3n) { animation-delay: 0.2s; }
	.sk-cell:nth-child(5n) { animation-delay: 0.4s; }

	@keyframes shimmer {
		0%, 100% { opacity: 0.35; }
		50% { opacity: 0.7; }
	}

	.chart-error {
		font-size: 13px;
		color: var(--red);
		padding: 12px 0;
	}

	/* Tooltip — fixed position, outside any scroll container */
	.tooltip {
		position: fixed;
		pointer-events: none;
		background: #1f1f2e;
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 5px 10px;
		font-size: 12px;
		color: var(--text);
		white-space: nowrap;
		z-index: 1000;
		box-shadow: 0 4px 16px rgba(0,0,0,0.4);
	}
</style>
