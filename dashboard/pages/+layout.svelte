<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { browser } from '$app/environment';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { setQueryFunction } from '@evidence-dev/component-utilities/buildQuery';
	import TopNavBar from '../components/TopNavBar.svelte';
	export let data;

	// Garante que todos os <Dropdown> aguardem database_initialization via data.__db.query
	// em vez de chamar client-duckdb diretamente (evitando timeout de 5s no mobile/4G).
	let activeQueryFn = data?.__db?.query;
	$: activeQueryFn = data?.__db?.query ?? activeQueryFn;
	if (browser && activeQueryFn) {
		setQueryFunction((sql, opts) => activeQueryFn(sql, opts));
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<EvidenceDefaultLayout
	{data}
	title="SidraLake 360°"
	homePageName="Executivo"
	neverShowQueries={true}
	fullWidth={true}
	hideTOC={true}
	hideSidebar={true}
	hideHeader={true}
	hideBreadcrumbs={true}
	builtWithEvidence={false}
	maxWidth={1440}
	githubRepo="https://github.com/leoserpa/sidralake"
>
	<TopNavBar />
	<slot slot="content" />
</EvidenceDefaultLayout>

<style>
	:global(:root) {
		color-scheme: dark;
		--sl-canvas: #191c1d;
		--sl-surface: #0b0f0d;
		--sl-elevated: #131716;
		--sl-border: #2d3231;
		--sl-border-subtle: #3a403e;
		--sl-divider: #1d2220;
		--sl-text-primary: #f5f7f6;
		--sl-text-secondary: #d4d8d6;
		--sl-text-muted: #9ca3a0;
		--sl-accent: #3b82f6;
		--sl-bar-muted: #525755;
	}

	:global(html),
	:global(body) {
		background-color: #191c1d !important;
		color: #f5f7f6 !important;
		font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
		font-variant-numeric: tabular-nums;
		-webkit-font-smoothing: antialiased;
	}

	:global(main) {
		margin-top: 22px !important;
		padding-bottom: 36px;
	}

	/* Hide Evidence auto-injected frontmatter H1 so our Figma header H1 is the single page title */
	:global(article#evidence-main-article > h1.title) {
		display: none !important;
	}

	/* Hide Evidence QueryViewer blocks completely (independent of Svelte hash & localStorage) */
	:global(article#evidence-main-article > div:has(> div > button[aria-label='view-query'])),
	:global(article#evidence-main-article > div:has(> div > div > button[aria-label='show-sql'])),
	:global(div:has(> button[aria-label='view-query'])),
	:global(button[aria-label='show-sql']),
	:global(button[aria-label='view-query']) {
		display: none !important;
	}

	:global(.sl-page-header) {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 18px;
		flex-wrap: wrap;
		margin-bottom: 20px;
	}

	:global(.sl-page-heading) {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
	}

	:global(.sl-page-title) {
		margin: 0 !important;
		color: #f5f7f6 !important;
		font-size: 23px !important;
		font-weight: 700 !important;
		line-height: 1.2 !important;
		letter-spacing: -0.025em !important;
	}

	:global(.sl-page-subtitle) {
		margin: 0 !important;
		color: #9ca3a0 !important;
		font-size: 13px !important;
		line-height: 1.45 !important;
	}

	:global(.sl-section-heading) {
		margin: 26px 0 14px 0 !important;
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
		flex-wrap: wrap;
	}

	:global(.sl-section-title) {
		margin: 0 !important;
		color: #f5f7f6 !important;
		font-size: 16px !important;
		font-weight: 600 !important;
		letter-spacing: -0.015em;
	}

	:global(.sl-section-sub) {
		color: #9ca3a0;
		font-size: 12px;
	}

	/* Inline filter pill ribbon */
	:global(.sl-filter-bar) {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}

	:global(.sl-filter-bar > *),
	:global(.sl-filter-bar > div > div),
	:global(.sl-filter-bar button[role='combobox']) {
		margin: 0 !important;
		display: inline-flex;
		align-items: center;
	}

	:global(.sl-filter-bar button) {
		background-color: #0b0f0d !important;
		border: 1px solid #2d3231 !important;
		border-radius: 6px !important;
		color: #d4d8d6 !important;
		font-size: 12.5px !important;
		height: 38px !important;
		min-height: 38px !important;
		padding-top: 0 !important;
		padding-bottom: 0 !important;
		box-sizing: border-box !important;
		display: inline-flex !important;
		align-items: center !important;
		line-height: 1 !important;
		box-shadow: none !important;
	}

	:global(.sl-filter-bar button:hover) {
		border-color: #464d4b !important;
		color: #f5f7f6 !important;
	}

	:global(.sl-filter-bar .sl-outline-pill) {
		height: 38px !important;
		padding: 0 12px !important;
		border-radius: 6px !important;
		box-sizing: border-box;
	}

	:global(.sl-filter-bar .sl-outline-pill.sl-city-a) {
		background: #3b82f6 !important;
		border-color: #3b82f6 !important;
		color: #ffffff !important;
		font-weight: 600 !important;
	}

	:global(.sl-filter-bar .sl-outline-pill.sl-city-b) {
		background: #686e6c !important;
		border-color: #686e6c !important;
		color: #f5f7f6 !important;
		font-weight: 600 !important;
	}

	/* Crisp unfilled outline pill (ZERO blue background shading) */
	:global(.sl-outline-pill) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 4px 11px;
		border-radius: 9999px;
		border: 1px solid #3a403e;
		background: transparent;
		color: #d4d8d6;
		font-size: 11.5px;
		font-weight: 500;
		line-height: 1.2;
		white-space: nowrap;
	}

	/* KPI strip responsive grids */
	:global(.sl-kpi-grid-5) {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 14px;
		margin-bottom: 18px;
	}

	:global(.sl-kpi-grid-6) {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 14px;
		margin-bottom: 18px;
	}

	:global(.sl-kpi-grid-4) {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 14px;
		margin-bottom: 18px;
	}

	/* 2-column chart card grid */
	:global(.sl-grid-2) {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 18px;
		margin-bottom: 18px;
	}

	:global(.sl-stack) {
		margin-bottom: 18px;
	}

	/* Matte Charcoal Recessed Card (#0B0F0D on #191C1D canvas, 1px #2D3231 border) */
	:global(.sl-card) {
		background: #0b0f0d;
		border: 1px solid #2d3231;
		border-radius: 10px;
		padding: 20px 22px;
		min-width: 0;
	}

	:global(.sl-card-title) {
		color: #f5f7f6;
		font-size: 15px;
		font-weight: 600;
		line-height: 1.3;
		letter-spacing: -0.015em;
	}

	:global(.sl-card-subtitle) {
		color: #9ca3a0;
		font-size: 12px;
		font-weight: 400;
		line-height: 1.4;
	}

	/* Filter strip card for sliders / side-by-side selectors */
	:global(.sl-control-card) {
		background: #0b0f0d;
		border: 1px solid #2d3231;
		border-radius: 10px;
		padding: 16px 20px;
		margin-bottom: 18px;
	}

	:global(.sl-slider-grid-3) {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 20px;
		align-items: end;
	}

	:global(.sl-slider-grid-2) {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 20px;
		align-items: center;
	}

	/* Clean ECharts container alignment inside recessed .sl-card */
	:global(.sl-card > div) {
		width: 100% !important;
		max-width: 100% !important;
	}

	:global(.sl-card .chart-container),
	:global(.sl-card .echarts),
	:global(.sl-card [data-testid='ECharts']) {
		background: transparent !important;
		width: 100% !important;
	}

	:global(.sl-card h3),
	:global(.sl-card h4) {
		color: #f5f7f6 !important;
	}

	:global(.sl-footer) {
		margin-top: 28px;
		padding-top: 16px;
		border-top: 1px solid #2d3231;
		color: #7c8380;
		font-size: 12px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		flex-wrap: wrap;
	}

	:global(.sl-footer strong) {
		color: #9ca3a0;
		font-weight: 600;
	}

	@media (max-width: 1200px) {
		:global(.sl-kpi-grid-6) {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		:global(.sl-kpi-grid-5) {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}

	@media (max-width: 960px) {
		:global(.sl-grid-2),
		:global(.sl-slider-grid-3),
		:global(.sl-slider-grid-2) {
			grid-template-columns: 1fr;
		}
		:global(.sl-kpi-grid-5),
		:global(.sl-kpi-grid-6),
		:global(.sl-kpi-grid-4) {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	@media (max-width: 768px) {
		:global(main) {
			margin-top: 14px !important;
			padding-bottom: 24px;
		}
		:global(.sl-page-header) {
			align-items: stretch;
			gap: 12px;
			margin-bottom: 14px;
		}
		:global(.sl-page-title) {
			font-size: 19px !important;
		}
		:global(.sl-page-subtitle) {
			font-size: 12.5px !important;
		}
		:global(.sl-filter-bar) {
			width: 100%;
			gap: 8px;
		}
		:global(.sl-card),
		:global(.sl-control-card) {
			padding: 14px 14px;
		}
		:global(.sl-footer) {
			flex-direction: column;
			align-items: flex-start;
			gap: 6px;
		}
	}

	@media (max-width: 560px) {
		:global(.sl-kpi-grid-5),
		:global(.sl-kpi-grid-6),
		:global(.sl-kpi-grid-4) {
			grid-template-columns: 1fr;
		}
	}
</style>
