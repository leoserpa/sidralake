<script>
	import { onDestroy } from 'svelte';
	import { addBasePath } from '@evidence-dev/sdk/utils/svelte';

	export let data = undefined;

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

	function formatTier(raw) {
		if (!raw) return '';
		return String(raw)
			.replace('Tier 1 - Polo Nacional', 'Tier 1 · Polo Nacional')
			.replace('Tier 2 - Expansao Prioritaria', 'Tier 2 · Expansão Prioritária')
			.replace('Tier 3 - Emergente', 'Tier 3 · Emergente')
			.replace('Tier 4 - Local / Nicho', 'Tier 4 · Local / Nicho');
	}

	$: row = rows[0] ?? null;
	$: cityName = row?.cidade_uf ?? 'Raio-X Municipal';
	$: tierLabel = formatTier(row?.tier_mercado);
</script>

<section class="sl-hero-card">
	<div class="sl-hero-left">
		<div class="sl-hero-title-row">
			<h1 class="sl-page-title">{cityName}</h1>
			{#if tierLabel}
				<span class="sl-outline-pill">{tierLabel}</span>
			{/if}
		</div>
		<p class="sl-hero-meta">
			{#if row}
				Região Imediata: {row.nome_regiao_imediata} · Região Intermediária: {row.nome_regiao_intermediaria} · Grande Região: {row.nome_regiao}
			{:else}
				Dossiê executivo 360° de todos os 5.571 municípios oficiais do IBGE
			{/if}
		</p>
	</div>

	<div class="sl-hero-actions">
		<div class="sl-filter-bar">
			<slot />
		</div>
		<a class="sl-primary-btn" href={addBasePath('/comparador/')}>
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d="m16 3 4 4-4 4" />
				<path d="M20 7H4" />
				<path d="m8 21-4-4 4-4" />
				<path d="M4 17h16" />
			</svg>
			<span>Comparar Cidade</span>
		</a>
	</div>
</section>

<style>
	.sl-hero-card {
		background: #0b0f0d;
		border: 1px solid #2d3231;
		border-radius: 10px;
		padding: 20px 24px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
		flex-wrap: wrap;
		margin-bottom: 18px;
	}

	.sl-hero-left {
		display: flex;
		flex-direction: column;
		gap: 6px;
		min-width: 0;
	}

	.sl-hero-title-row {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.sl-hero-meta {
		margin: 0;
		color: #9ca3a0;
		font-size: 12.5px;
		line-height: 1.4;
	}

	.sl-hero-actions {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	.sl-primary-btn {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		height: 36px;
		padding: 0 14px;
		border-radius: 6px;
		background: #3b82f6;
		color: #ffffff;
		font-size: 12.5px;
		font-weight: 600;
		text-decoration: none;
		white-space: nowrap;
		transition: background 0.15s ease;
	}

	.sl-primary-btn:hover {
		background: #2563eb;
	}
</style>
