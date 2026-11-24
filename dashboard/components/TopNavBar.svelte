<script>
	import { page } from '$app/stores';
	import { addBasePath } from '@evidence-dev/sdk/utils/svelte';

	const NAV_ITEMS = [
		{ label: 'Executivo', path: '/' },
		{ label: 'Raio-X', path: '/municipio/' },
		{ label: 'Comparador', path: '/comparador/' },
		{ label: 'Expansão', path: '/expansao/' },
		{ label: 'Dinamismo', path: '/dinamismo/' },
		{ label: 'Demografia', path: '/demografia/' },
		{ label: 'Trabalho', path: '/trabalho/' },
		{ label: 'CNAE', path: '/clusters-cnae/' },
		{ label: 'Varejo', path: '/pulso-varejo/' }
	];

	function normalizePath(p) {
		if (!p) return '/';
		let cleaned = p.replace(/^\/sidralake(?=\/|$)/, '') || '/';
		if (!cleaned.startsWith('/')) cleaned = '/' + cleaned;
		if (cleaned.length > 1 && cleaned.endsWith('/')) cleaned = cleaned.slice(0, -1);
		return cleaned;
	}

	$: currentPath = normalizePath($page?.url?.pathname ?? '/');

	function isActive(targetPath, activePath) {
		return normalizePath(targetPath) === activePath;
	}
</script>

<header class="sl-topbar">
	<div class="sl-topbar-inner">
		<a class="sl-brand" href={addBasePath('/')}>
			<span class="sl-brand-mark" aria-hidden="true">
				<svg width="28" height="28" viewBox="0 0 128 128" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M113.445 37.7096C122.779 55.2646 108.209 81.2663 80.901 95.7861C53.5932 110.306 23.8891 107.845 14.5549 90.2904C5.22079 72.7354 19.7913 46.7337 47.099 32.2139C74.4068 17.6941 104.111 20.1546 113.445 37.7096Z" stroke="#3B82F6" stroke-width="6"/>
					<path d="M64 62L94 78V90L64 107L34 90V78L64 62Z" fill="#3B82F6" stroke="#0B0F0D" stroke-width="4" stroke-linejoin="round"/>
					<path d="M64 42L94 58V70L64 87L34 70V58L64 42Z" fill="#3B82F6" stroke="#0B0F0D" stroke-width="4" stroke-linejoin="round"/>
					<path d="M64 22L94 38V50L64 67L34 50V38L64 22Z" fill="#3B82F6" stroke="#0B0F0D" stroke-width="4" stroke-linejoin="round"/>
					<path d="M64 29L86 41L64 53L42 41L64 29Z" fill="#F5F7F6"/>
				</svg>
			</span>
			<span class="sl-brand-name">SidraLake</span>
			<span class="sl-brand-tag">360°</span>
		</a>

		<nav class="sl-nav" aria-label="Navegação principal">
			{#each NAV_ITEMS as item}
				{@const active = isActive(item.path, currentPath)}
				<a
					class="sl-nav-link"
					class:is-active={active}
					href={addBasePath(item.path)}
					aria-current={active ? 'page' : undefined}
				>
					{item.label}
				</a>
			{/each}
		</nav>

		<div class="sl-status-pill" title="Dados públicos oficiais IBGE executados localmente no navegador">
			<span class="sl-status-source">IBGE Oficial</span>
			<span class="sl-status-sep" aria-hidden="true"></span>
			<span class="sl-status-engine">DuckDB-WASM</span>
		</div>
	</div>
</header>

<style>
	.sl-topbar {
		position: sticky;
		top: 0;
		z-index: 40;
		width: 100%;
		height: 60px;
		background: #0b0f0d;
		border-bottom: 1px solid #2d3231;
	}

	.sl-topbar-inner {
		max-width: 1440px;
		height: 100%;
		margin: 0 auto;
		padding: 0 32px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
	}

	.sl-brand {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		text-decoration: none;
		flex-shrink: 0;
	}

	.sl-brand-mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.sl-brand-name {
		color: #f5f7f6;
		font-size: 16px;
		font-weight: 700;
		letter-spacing: -0.025em;
	}

	.sl-brand-tag {
		background: transparent;
		border: none;
		padding: 0;
		color: #3b82f6;
		font-size: 13px;
		font-weight: 700;
		line-height: 1;
		letter-spacing: -0.01em;
	}

	.sl-nav {
		display: flex;
		align-items: center;
		gap: 26px;
		height: 100%;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.sl-nav::-webkit-scrollbar {
		display: none;
	}

	.sl-nav-link {
		position: relative;
		display: inline-flex;
		align-items: center;
		height: 100%;
		color: #9ca3a0;
		font-size: 13px;
		font-weight: 500;
		text-decoration: none;
		white-space: nowrap;
		transition: color 0.15s ease;
	}

	.sl-nav-link:hover {
		color: #e5e8e6;
	}

	.sl-nav-link.is-active {
		color: #f5f7f6;
		font-weight: 600;
	}

	.sl-nav-link.is-active::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 2px;
		background: #3b82f6;
		border-radius: 2px 2px 0 0;
	}

	.sl-status-pill {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 0;
		border: none;
		background: transparent;
		font-size: 12px;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.sl-status-source {
		color: #f5f7f6;
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.sl-status-sep {
		width: 1px;
		height: 12px;
		background: #3a403e;
		flex-shrink: 0;
	}

	.sl-status-engine {
		color: #9ca3a0;
		font-size: 11.5px;
		font-weight: 500;
	}

	@media (max-width: 1024px) {
		.sl-topbar-inner {
			padding: 0 18px;
		}
		.sl-status-pill {
			display: none;
		}
		.sl-nav {
			gap: 18px;
		}
	}
</style>
