<script>
	import { onDestroy } from 'svelte';

	export let data = undefined;
	export let labelCol = 'regiao';
	export let valueCol = 'pib_real_bi';
	export let title = 'Como o PIB real se distribui por Região?';
	export let centerLabel = 'PIB Real Total';

	const PALETTE = ['#3b82f6', '#64748b', '#525866', '#475569', '#334155', '#1e293b'];
	const nfDec2 = new Intl.NumberFormat('pt-BR', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});
	const nfDec1 = new Intl.NumberFormat('pt-BR', {
		minimumFractionDigits: 1,
		maximumFractionDigits: 1
	});

	let rows = [];
	let hoveredIndex = -1;
	let unsub = () => {};

	function isQueryStore(d) {
		return Boolean(d && typeof d.fetch === 'function' && typeof d.subscribe === 'function');
	}

	$: {
		unsub();
		unsub = () => {};
		if (isQueryStore(data)) {
			data.fetch();
			unsub = data.subscribe((v) => {
				rows = Array.from(v ?? []);
			});
		} else if (Array.isArray(data)) {
			rows = data;
		} else {
			rows = [];
		}
	}

	onDestroy(() => unsub());

	$: totalBi = rows.reduce((acc, r) => acc + Number(r[valueCol] || 0), 0);
	$: leader = rows[0] ?? null;
	$: leaderShare = leader && totalBi > 0 ? (Number(leader[valueCol] || 0) / totalBi) * 100 : 0;

	function fmtTotal(bi) {
		if (!bi || bi <= 0) return '—';
		return bi >= 1000 ? `R$ ${nfDec2.format(bi / 1000)} Tri` : `R$ ${nfDec1.format(bi)} Bi`;
	}

	function polarToCartesian(cx, cy, r, angleDeg) {
		const rad = ((angleDeg - 90) * Math.PI) / 180;
		return {
			x: cx + r * Math.cos(rad),
			y: cy + r * Math.sin(rad)
		};
	}

	function buildArcPath(cx, cy, outerR, innerR, startAngle, endAngle) {
		const sweep = Math.min(endAngle - startAngle, 359.95);
		const end = startAngle + sweep;
		const p1 = polarToCartesian(cx, cy, outerR, startAngle);
		const p2 = polarToCartesian(cx, cy, outerR, end);
		const p3 = polarToCartesian(cx, cy, innerR, end);
		const p4 = polarToCartesian(cx, cy, innerR, startAngle);
		const largeArc = sweep > 180 ? 1 : 0;
		return [
			`M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`,
			`A ${outerR} ${outerR} 0 ${largeArc} 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`,
			`L ${p3.x.toFixed(2)} ${p3.y.toFixed(2)}`,
			`A ${innerR} ${innerR} 0 ${largeArc} 0 ${p4.x.toFixed(2)} ${p4.y.toFixed(2)}`,
			'Z'
		].join(' ');
	}

	$: slices = (() => {
		if (!totalBi) return [];
		let cursor = 0;
		return rows.map((r, idx) => {
			const val = Number(r[valueCol] || 0);
			const pct = (val / totalBi) * 100;
			const angle = (val / totalBi) * 360;
			const start = cursor;
			const end = cursor + angle;
			cursor = end;
			return {
				label: String(r[labelCol] ?? ''),
				val,
				pct,
				color: PALETTE[idx] ?? '#334155',
				isLeader: idx === 0,
				path: buildArcPath(96, 96, 86, 56, start, end)
			};
		});
	})();

	$: activeSlice = hoveredIndex >= 0 ? slices[hoveredIndex] : null;
</script>

<div class="sl-donut-wrap">
	<div class="sl-donut-head">
		<div class="sl-card-title">{title}</div>
		<div class="sl-card-subtitle">
			{#if leader}
				Participação regional (R$ Tri) · {leader[labelCol]} concentra {nfDec1.format(leaderShare)}%
			{:else}
				Participação regional no PIB real
			{/if}
		</div>
	</div>

	<div class="sl-donut-body">
		<div class="sl-donut-chart">
			<svg viewBox="0 0 192 192" class="sl-donut-svg" role="img" aria-label={title}>
				{#each slices as s, idx}
					<path
						d={s.path}
						fill={s.color}
						stroke="#0f141d"
						stroke-width="2.5"
						class="sl-donut-slice"
						class:is-dimmed={hoveredIndex >= 0 && hoveredIndex !== idx}
						on:mouseenter={() => (hoveredIndex = idx)}
						on:mouseleave={() => (hoveredIndex = -1)}
					/>
				{/each}
			</svg>
			<div class="sl-donut-center">
				<div class="sl-donut-total">
					{activeSlice ? fmtTotal(activeSlice.val) : fmtTotal(totalBi)}
				</div>
				<div class="sl-donut-caption">
					{activeSlice ? `${activeSlice.label} · ${nfDec1.format(activeSlice.pct)}%` : centerLabel}
				</div>
			</div>
		</div>

		<ul class="sl-donut-legend">
			{#each slices as s, idx}
				<li
					class="sl-legend-row"
					class:is-leader={s.isLeader}
					class:is-hovered={hoveredIndex === idx}
					on:mouseenter={() => (hoveredIndex = idx)}
					on:mouseleave={() => (hoveredIndex = -1)}
				>
					<span class="sl-legend-left">
						<span class="sl-legend-dot" style="background: {s.color}"></span>
						<span class="sl-legend-name">{s.label}</span>
					</span>
					<span class="sl-legend-right">
						<span class="sl-legend-val">{fmtTotal(s.val)}</span>
						<span class="sl-legend-pct" class:is-accent={s.isLeader}>
							{nfDec1.format(s.pct)}%
						</span>
					</span>
				</li>
			{/each}
		</ul>
	</div>
</div>

<style>
	.sl-donut-wrap {
		display: flex;
		flex-direction: column;
		height: 100%;
		justify-content: space-between;
		gap: 18px;
	}

	.sl-donut-head {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.sl-donut-body {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 28px;
		flex: 1;
		padding: 6px 4px;
	}

	.sl-donut-chart {
		position: relative;
		width: 196px;
		height: 196px;
		flex-shrink: 0;
	}

	.sl-donut-svg {
		width: 100%;
		height: 100%;
		display: block;
	}

	.sl-donut-slice {
		cursor: pointer;
		transition: opacity 0.15s ease;
	}

	.sl-donut-slice.is-dimmed {
		opacity: 0.45;
	}

	.sl-donut-center {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		pointer-events: none;
		padding: 0 22px;
	}

	.sl-donut-total {
		color: #f8fafc;
		font-size: 16px;
		font-weight: 700;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}

	.sl-donut-caption {
		color: #94a3b8;
		font-size: 11px;
		margin-top: 2px;
	}

	.sl-donut-legend {
		list-style: none;
		margin: 0;
		padding: 0;
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.sl-legend-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		cursor: default;
		transition: opacity 0.15s ease;
	}

	.sl-legend-left {
		display: inline-flex;
		align-items: center;
		gap: 9px;
		min-width: 0;
	}

	.sl-legend-dot {
		width: 8px;
		height: 8px;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.sl-legend-name {
		color: #cbd5e1;
		font-size: 13px;
		font-weight: 400;
	}

	.sl-legend-row.is-leader .sl-legend-name {
		color: #f8fafc;
		font-weight: 600;
	}

	.sl-legend-right {
		display: inline-flex;
		align-items: center;
		gap: 14px;
		font-variant-numeric: tabular-nums;
		flex-shrink: 0;
	}

	.sl-legend-val {
		color: #94a3b8;
		font-size: 12.5px;
	}

	.sl-legend-pct {
		color: #cbd5e1;
		font-size: 12.5px;
		font-weight: 600;
		min-width: 44px;
		text-align: right;
	}

	.sl-legend-pct.is-accent {
		color: #3b82f6;
	}

	@media (max-width: 640px) {
		.sl-donut-body {
			flex-direction: column;
			align-items: stretch;
		}
		.sl-donut-chart {
			margin: 0 auto;
		}
	}
</style>
