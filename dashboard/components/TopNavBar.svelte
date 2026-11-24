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
				<svg width="26" height="26" viewBox="0 0 26 26" fill="none">
					<rect width="26" height="26" rx="6" fill="#3B82F6" />
					<rect x="6" y="14" width="3" height="6" rx="1" fill="#F8FAFC" />
					<rect x="11.5" y="10" width="3" height="10" rx="1" fill="#F8FAFC" />
					<rect x="17" y="6" width="3" height="14" rx="1" fill="#F8FAFC" />
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
			<span class="sl-status-dot" aria-hidden="true"></span>
			<span>IBGE Oficial · DuckDB-WASM</span>
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
		gap: 10px;
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
		font-size: 15px;
		font-weight: 700;
		letter-spacing: -0.02em;
	}

	.sl-brand-tag {
		display: inline-flex;
		align-items: center;
		padding: 2px 7px;
		border-radius: 5px;
		border: 1px solid #3a403e;
		background: transparent;
		color: #9ca3a0;
		font-size: 11px;
		font-weight: 600;
		line-height: 1.2;
		letter-spacing: 0.01em;
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
		padding: 6px 12px;
		border-radius: 9999px;
		background: #131716;
		border: 1px solid #2d3231;
		color: #d4d8d6;
		font-size: 11.5px;
		font-weight: 500;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.sl-status-dot {
		width: 6px;
		height: 6px;
		border-radius: 9999px;
		background: #3b82f6;
		flex-shrink: 0;
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
