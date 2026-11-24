<script>
	function resetFilters() {
		if (typeof window !== 'undefined') {
			window.location.assign(window.location.pathname);
		}
	}
</script>

<button
	type="button"
	class="sl-reset-filters-btn"
	on:click={resetFilters}
	title="Restaurar todos os filtros para o padrão"
>
	<svg
		xmlns="http://www.w3.org/2000/svg"
		width="14"
		height="14"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.8"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
		<path d="M3 3v5h5" />
	</svg>
	<span>Limpar filtros</span>
</button>

<style>
	.sl-reset-filters-btn {
		background: #0b0f0d;
		border: 1px solid #2d3231;
		border-radius: 6px;
		color: #9ca3a0;
		height: 38px;
		padding: 0 12px;
		font-size: 0.78rem;
		font-weight: 500;
		line-height: 1;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		white-space: nowrap;
		cursor: pointer;
		transition: border-color 140ms ease, color 140ms ease, background-color 140ms ease;
	}

	.sl-reset-filters-btn:hover,
	.sl-reset-filters-btn:focus-visible {
		border-color: #464d4b;
		color: #f5f7f6;
		background: #131716;
		outline: none;
	}
</style>
