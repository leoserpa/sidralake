<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import TopNavBar from '../components/TopNavBar.svelte';
	export let data;
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
		--sl-canvas: #090d14;
		--sl-surface: #0f141d;
		--sl-elevated: #141b26;
		--sl-border: #1e293b;
		--sl-border-subtle: #334155;
		--sl-text-primary: #f8fafc;
		--sl-text-secondary: #cbd5e1;
		--sl-text-muted: #94a3b8;
		--sl-accent: #3b82f6;
		--sl-bar-muted: #525866;
	}

	:global(html),
	:global(body) {
		background-color: #090d14 !important;
		color: #f8fafc !important;
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
		color: #f8fafc !important;
		font-size: 23px !important;
		font-weight: 700 !important;
		line-height: 1.2 !important;
		letter-spacing: -0.025em !important;
	}

	:global(.sl-page-subtitle) {
		margin: 0 !important;
		color: #94a3b8 !important;
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
		color: #f8fafc !important;
		font-size: 16px !important;
		font-weight: 600 !important;
		letter-spacing: -0.015em;
	}

	:global(.sl-section-sub) {
		color: #94a3b8;
		font-size: 12px;
	}

	/* Inline filter pill ribbon matching Figma FilterPill */
	:global(.sl-filter-bar) {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}

	:global(.sl-filter-bar > div),
	:global(.sl-filter-bar button[role='combobox']) {
		margin: 0 !important;
	}

	:global(.sl-filter-bar button) {
		background-color: #141b26 !important;
		border: 1px solid #334155 !important;
		border-radius: 6px !important;
		color: #cbd5e1 !important;
		font-size: 12.5px !important;
		min-height: 36px;
		box-shadow: none !important;
	}

	:global(.sl-filter-bar button:hover) {
		border-color: #475569 !important;
		color: #f8fafc !important;
	}

	/* Crisp unfilled outline pill (ZERO blue background shading) */
	:global(.sl-outline-pill) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 4px 11px;
		border-radius: 9999px;
		border: 1px solid #334155;
		background: transparent;
		color: #cbd5e1;
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

	/* Elevated Obsidian Card (10px radius, 1px #1E293B border, zero shadow) */
	:global(.sl-card) {
		background: #0f141d;
		border: 1px solid #1e293b;
		border-radius: 10px;
		padding: 20px 22px;
		min-width: 0;
	}

	:global(.sl-card-title) {
		color: #f8fafc;
		font-size: 15px;
		font-weight: 600;
		line-height: 1.3;
		letter-spacing: -0.015em;
	}

	:global(.sl-card-subtitle) {
		color: #94a3b8;
		font-size: 12px;
		font-weight: 400;
		line-height: 1.4;
	}

	/* Filter strip card for sliders / side-by-side selectors */
	:global(.sl-control-card) {
		background: #0f141d;
		border: 1px solid #1e293b;
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
		align-items: end;
	}

	/* Clean ECharts container alignment inside elevated .sl-card */
	:global(.sl-card .chart-container),
	:global(.sl-card .echarts) {
		background: transparent !important;
	}

	:global(.sl-card h3),
	:global(.sl-card h4) {
		color: #f8fafc !important;
	}

	:global(.sl-footer) {
		margin-top: 28px;
		padding-top: 16px;
		border-top: 1px solid #1e293b;
		color: #64748b;
		font-size: 12px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		flex-wrap: wrap;
	}

	:global(.sl-footer strong) {
		color: #94a3b8;
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

	@media (max-width: 560px) {
		:global(.sl-kpi-grid-5),
		:global(.sl-kpi-grid-6),
		:global(.sl-kpi-grid-4) {
			grid-template-columns: 1fr;
		}
	}
</style>
