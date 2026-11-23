<script>
	import { onDestroy } from 'svelte';

	export let data = undefined;
	export let value = '';
	export let title = '';
	export let subtitle = '';
	export let subtitleCol = '';
	export let subtitleFmt = 'raw';
	export let subtitlePrefix = '';
	export let subtitleSuffix = '';
	export let subtitle2Col = '';
	export let subtitle2Fmt = 'raw';
	export let subtitle2Prefix = '';
	export let subtitle2Suffix = '';
	export let fmt = 'raw';
	export let icon = 'gauge';

	let rows = [];
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

	const nfInt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
	const nfDec1 = new Intl.NumberFormat('pt-BR', {
		minimumFractionDigits: 1,
		maximumFractionDigits: 1
	});
	const nfDec2 = new Intl.NumberFormat('pt-BR', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});

	function formatValue(raw, format) {
		if (raw === null || raw === undefined || raw === '') return '—';
		if (format === 'raw') return String(raw);
		const num = Number(raw);
		if (Number.isNaN(num)) return String(raw);

		switch (format) {
			case 'brl_tri':
				return `R$ ${nfDec2.format(num)} Tri`;
			case 'brl_bi':
				return num >= 1000
					? `R$ ${nfDec2.format(num / 1000)} Tri`
					: `R$ ${nfDec1.format(num)} Bi`;
			case 'brl_bi_exact':
				return `R$ ${nfDec1.format(num)} Bi`;
			case 'brl_int':
				return `R$ ${nfInt.format(Math.round(num))}`;
			case 'pop_mi':
				return num >= 1_000_000
					? `${nfDec2.format(num / 1_000_000)} Mi`
					: num >= 1_000
						? `${nfDec1.format(num / 1_000)} mil`
						: nfInt.format(Math.round(num));
			case 'int':
				return nfInt.format(Math.round(num));
			case 'dec1':
				return nfDec1.format(num);
			case 'dec2':
				return nfDec2.format(num);
			case 'pct1':
				return `${nfDec1.format(num * 100)}%`;
			case 'pct2':
				return `${nfDec2.format(num * 100)}%`;
			case 'signed_pct2': {
				const sign = num > 0 ? '+' : '';
				return `${sign}${nfDec2.format(num * 100)}%`;
			}
			case 'rank':
				return `#${nfInt.format(Math.round(num))}`;
			default:
				return String(raw);
		}
	}

	$: row = rows[0] ?? null;
	$: displayValue = row ? formatValue(row[value], fmt) : '—';
	$: displaySubtitle = (() => {
		if (!subtitleCol) return subtitle;
		if (!row) return subtitle || ' ';
		const part1 =
			row[subtitleCol] !== null && row[subtitleCol] !== undefined
				? `${subtitlePrefix}${formatValue(row[subtitleCol], subtitleFmt)}${subtitleSuffix}`
				: '';
		const part2 =
			subtitle2Col && row[subtitle2Col] !== null && row[subtitle2Col] !== undefined
				? `${subtitle2Prefix}${formatValue(row[subtitle2Col], subtitle2Fmt)}${subtitle2Suffix}`
				: '';
		return `${part1}${part2}`.trim() || subtitle;
	})();
</script>

<div class="sl-kpi-card">
	<div class="sl-kpi-top">
		<span class="sl-kpi-title">{title}</span>
		<span class="sl-kpi-icon" aria-hidden="true">
			{#if icon === 'landmark'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<line x1="3" y1="22" x2="21" y2="22" />
					<line x1="6" y1="18" x2="6" y2="11" />
					<line x1="10" y1="18" x2="10" y2="11" />
					<line x1="14" y1="18" x2="14" y2="11" />
					<line x1="18" y1="18" x2="18" y2="11" />
					<polygon points="12 2 20 7 4 7" />
				</svg>
			{:else if icon === 'users'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
					<circle cx="9" cy="7" r="4" />
					<path d="M22 21v-2a4 4 0 0 0-3-3.87" />
					<path d="M16 3.13a4 4 0 0 1 0 7.75" />
				</svg>
			{:else if icon === 'briefcase'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
					<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
				</svg>
			{:else if icon === 'percent'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<line x1="19" y1="5" x2="5" y2="19" />
					<circle cx="6.5" cy="6.5" r="2.5" />
					<circle cx="17.5" cy="17.5" r="2.5" />
				</svg>
			{:else if icon === 'trophy'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
					<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
					<path d="M4 22h16" />
					<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
					<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
					<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
				</svg>
			{:else if icon === 'mappin'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
					<circle cx="12" cy="10" r="3" />
				</svg>
			{:else if icon === 'wallet'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
					<path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
					<path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
				</svg>
			{:else if icon === 'building'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
					<path d="M9 22v-4h6v4" />
					<path d="M8 6h.01" />
					<path d="M16 6h.01" />
					<path d="M12 6h.01" />
					<path d="M12 10h.01" />
					<path d="M12 14h.01" />
					<path d="M16 10h.01" />
					<path d="M16 14h.01" />
					<path d="M8 10h.01" />
					<path d="M8 14h.01" />
				</svg>
			{:else if icon === 'calendar'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
					<line x1="16" y1="2" x2="16" y2="6" />
					<line x1="8" y1="2" x2="8" y2="6" />
					<line x1="3" y1="10" x2="21" y2="10" />
				</svg>
			{:else if icon === 'trending'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
					<polyline points="16 7 22 7 22 13" />
				</svg>
			{:else if icon === 'shield'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
				</svg>
			{:else if icon === 'layers'}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<polygon points="12 2 2 7 12 12 22 7 12 2" />
					<polyline points="2 17 12 22 22 17" />
					<polyline points="2 12 12 17 22 12" />
				</svg>
			{:else}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
					<path d="m12 14 4-4" />
					<path d="M3.34 19a10 10 0 1 1 17.32 0" />
				</svg>
			{/if}
		</span>
	</div>

	<div class="sl-kpi-value">{displayValue}</div>

	{#if displaySubtitle}
		<div class="sl-kpi-sub">{displaySubtitle}</div>
	{/if}
</div>

<style>
	.sl-kpi-card {
		background: #0f141d;
		border: 1px solid #1e293b;
		border-radius: 10px;
		padding: 16px 18px;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		gap: 8px;
		min-height: 112px;
	}

	.sl-kpi-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}

	.sl-kpi-title {
		color: #94a3b8;
		font-size: 12px;
		font-weight: 500;
		line-height: 1.3;
	}

	.sl-kpi-icon {
		color: #94a3b8;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.sl-kpi-value {
		color: #f8fafc;
		font-size: 24px;
		font-weight: 700;
		line-height: 1.15;
		letter-spacing: -0.025em;
		font-variant-numeric: tabular-nums;
	}

	.sl-kpi-sub {
		color: #94a3b8;
		font-size: 11.5px;
		font-weight: 400;
		line-height: 1.35;
		font-variant-numeric: tabular-nums;
	}
</style>
