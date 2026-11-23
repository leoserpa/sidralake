<script>
	import { onDestroy } from 'svelte';

	export let data = undefined;
	export let columns = [];
	export let title = '';
	export let subtitle = '';
	export let search = false;
	export let searchPlaceholder = 'Buscar...';
	export let exportCsv = false;
	export let csvFilename = 'sidralake_export.csv';
	export let rowsPerPage = 15;
	export let highlightFirstRow = false;
	export let highlightRowKey = '';
	export let highlightRowValue = '';
	export let compact = false;

	let rawRows = [];
	let searchQuery = '';
	let sortKey = '';
	let sortDir = 'asc';
	let currentPage = 1;
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
				rawRows = Array.from(v ?? []);
				currentPage = 1;
			});
		} else if (Array.isArray(data)) {
			rawRows = data;
			currentPage = 1;
		} else {
			rawRows = [];
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
	const nfDec3 = new Intl.NumberFormat('pt-BR', {
		minimumFractionDigits: 3,
		maximumFractionDigits: 3
	});

	function formatCell(val, fmt) {
		if (val === null || val === undefined || val === '') return '—';
		if (!fmt || fmt === 'raw') return String(val);
		const num = Number(val);
		if (Number.isNaN(num)) return String(val);

		switch (fmt) {
			case 'rank':
				return `#${nfInt.format(Math.round(num))}`;
			case 'int':
				return nfInt.format(Math.round(num));
			case 'dec1':
				return nfDec1.format(num);
			case 'dec2':
				return nfDec2.format(num);
			case 'dec3':
				return nfDec3.format(num);
			case 'brl_int':
				return `R$ ${nfInt.format(Math.round(num))}`;
			case 'brl_bi':
				return `R$ ${nfDec1.format(num)} Bi`;
			case 'brl_bi2':
				return `R$ ${nfDec2.format(num)} Bi`;
			case 'brl_mi':
				return `R$ ${nfDec1.format(num)} Mi`;
			case 'pct1':
				return `${nfDec1.format(num * 100)}%`;
			case 'pct2':
				return `${nfDec2.format(num * 100)}%`;
			case 'signed_pct1': {
				const sign = num > 0 ? '+' : '';
				return `${sign}${nfDec1.format(num * 100)}%`;
			}
			case 'signed_pp': {
				const sign = num > 0 ? '+' : '';
				return `${sign}${nfDec2.format(num)} p.p.`;
			}
			case 'sm':
				return `${nfDec2.format(num)} SM`;
			default:
				return String(val);
		}
	}

	function formatTierBadge(raw) {
		if (raw === null || raw === undefined || raw === '') return '—';
		const s = String(raw);
		if (s === 'Tier 1' || s === 'Tier 1 - Polo Nacional') return 'Tier 1 · Polo';
		if (s === 'Tier 2' || s === 'Tier 2 - Expansao Prioritaria') return 'Tier 2 · Expansão';
		if (s === 'Tier 3' || s === 'Tier 3 - Emergente') return 'Tier 3 · Emergente';
		if (s === 'Tier 4' || s === 'Tier 4 - Local / Nicho') return 'Tier 4 · Local';
		return s;
	}

	function barPercent(val, maxVal) {
		const num = Number(val);
		if (Number.isNaN(num) || !maxVal) return 0;
		return Math.max(0, Math.min(100, (num / maxVal) * 100));
	}

	function isRowHighlighted(row, rowIdx) {
		if (highlightRowKey) {
			return String(row[highlightRowKey] ?? '') === String(highlightRowValue);
		}
		if (highlightFirstRow) {
			return rowIdx === 0;
		}
		return false;
	}

	function toggleSort(key) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = 'desc';
		}
		currentPage = 1;
	}

	$: normalizedQuery = searchQuery.trim().toLowerCase();

	$: filteredRows = (() => {
		if (!normalizedQuery) return rawRows;
		return rawRows.filter((row) =>
			columns.some((col) => {
				const v = row[col.key];
				return v !== null && v !== undefined && String(v).toLowerCase().includes(normalizedQuery);
			})
		);
	})();

	$: sortedRows = (() => {
		if (!sortKey) return filteredRows;
		const dir = sortDir === 'asc' ? 1 : -1;
		return [...filteredRows].sort((a, b) => {
			const av = a[sortKey];
			const bv = b[sortKey];
			if (av === null || av === undefined) return 1;
			if (bv === null || bv === undefined) return -1;
			const an = Number(av);
			const bn = Number(bv);
			if (!Number.isNaN(an) && !Number.isNaN(bn)) {
				return (an - bn) * dir;
			}
			return String(av).localeCompare(String(bv), 'pt-BR') * dir;
		});
	})();

	$: pageSize = Math.max(1, Number(rowsPerPage) || 15);
	$: totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
	$: safePage = Math.min(currentPage, totalPages);
	$: startIdx = (safePage - 1) * pageSize;
	$: pageRows = sortedRows.slice(startIdx, startIdx + pageSize);

	function downloadCsv() {
		if (typeof document === 'undefined' || !sortedRows.length) return;
		const escapeCsv = (val) => {
			if (val === null || val === undefined) return '';
			const str = String(val);
			return /[",\n;]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
		};
		const header = columns.map((c) => escapeCsv(c.label)).join(',');
		const body = sortedRows
			.map((r) => columns.map((c) => escapeCsv(r[c.key])).join(','))
			.join('\n');
		const blob = new Blob([`\uFEFF${header}\n${body}`], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = csvFilename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}
</script>

<section class="sl-table-card" class:is-compact={compact}>
	{#if title || subtitle || search || exportCsv}
		<div class="sl-table-header">
			<div class="sl-table-heading">
				{#if title}
					<div class="sl-card-title">{title}</div>
				{/if}
				{#if subtitle}
					<div class="sl-card-subtitle">{subtitle}</div>
				{/if}
			</div>

			{#if search || exportCsv}
				<div class="sl-table-controls">
					{#if search}
						<label class="sl-search-box">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<circle cx="11" cy="11" r="8" />
								<path d="m21 21-4.3-4.3" />
							</svg>
							<input
								type="search"
								bind:value={searchQuery}
								on:input={() => (currentPage = 1)}
								placeholder={searchPlaceholder}
								aria-label={searchPlaceholder}
							/>
						</label>
					{/if}
					{#if exportCsv}
						<button type="button" class="sl-export-btn" on:click={downloadCsv}>
							<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
								<polyline points="7 10 12 15 17 10" />
								<line x1="12" y1="15" x2="12" y2="3" />
							</svg>
							<span>Exportar CSV</span>
						</button>
					{/if}
				</div>
			{/if}
		</div>
	{/if}

	<div class="sl-table-scroll">
		<table class="sl-table">
			<thead>
				<tr>
					{#each columns as col}
						<th
							class:is-right={col.align === 'right'}
							class:is-center={col.align === 'center'}
							class:is-sorted={sortKey === col.key}
							aria-sort={sortKey === col.key
								? sortDir === 'asc'
									? 'ascending'
									: 'descending'
								: 'none'}
						>
							<button
								type="button"
								class="sl-th-btn"
								on:click={() => toggleSort(col.key)}
								title="Clique para ordenar"
							>
								<span>{col.label}</span>
								{#if sortKey === col.key}
									<span class="sl-sort-arrow" aria-hidden="true">{sortDir === 'asc' ? '↑' : '↓'}</span>
								{/if}
							</button>
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#if pageRows.length === 0}
					<tr>
						<td colspan={Math.max(1, columns.length)} class="sl-empty-cell">
							Nenhum registro encontrado para os filtros selecionados.
						</td>
					</tr>
				{:else}
					{#each pageRows as row, localIdx}
						{@const globalIdx = startIdx + localIdx}
						{@const isLeader = isRowHighlighted(row, globalIdx)}
						<tr class:is-leader={isLeader}>
							{#each columns as col}
								{@const rawVal = row[col.key]}
								{@const numVal = rawVal !== null && rawVal !== undefined ? Number(rawVal) : NaN}
								<td
									class:is-right={col.align === 'right'}
									class:is-center={col.align === 'center'}
								>
									{#if col.kind === 'rank'}
										<span class="sl-cell-rank" class:is-accent={isLeader}>
											{formatCell(rawVal, 'rank')}
										</span>
									{:else if col.kind === 'year'}
										<span class="sl-cell-primary" class:is-accent={isLeader}>
											{rawVal ?? '—'}
										</span>
									{:else if col.kind === 'primary'}
										<span class="sl-cell-primary">{rawVal ?? '—'}</span>
									{:else if col.kind === 'databar'}
										{@const hitBar =
											!Number.isNaN(numVal) &&
											((col.barThreshold !== undefined && numVal >= col.barThreshold) ||
												(col.barThreshold === undefined && isLeader))}
										<div class="sl-bar-cell">
											<span class="sl-bar-num" class:is-accent={hitBar}>
												{formatCell(rawVal, col.fmt || 'dec2')}
											</span>
											<div class="sl-bar-track" aria-hidden="true">
												<div
													class="sl-bar-fill"
													class:is-accent={hitBar}
													style="width: {barPercent(rawVal, col.barMax ?? 100)}%"
												></div>
											</div>
										</div>
									{:else if col.kind === 'growth'}
										{@const hitGrowth =
											!Number.isNaN(numVal) &&
											col.highlightThreshold !== undefined &&
											numVal >= col.highlightThreshold}
										<span class="sl-growth-cell" class:is-accent={hitGrowth}>
											{#if hitGrowth}
												<span class="sl-tri" aria-hidden="true">▲</span>
											{/if}
											{formatCell(rawVal, col.fmt || 'signed_pct1')}
										</span>
									{:else if col.kind === 'tier_badge'}
										<span class="sl-outline-pill">{formatTierBadge(rawVal)}</span>
									{:else if col.kind === 'sigilo_badge'}
										{#if rawVal === true || rawVal === 'true'}
											<span class="sl-outline-pill">Sigilo (X)</span>
										{:else}
											<span class="sl-muted">—</span>
										{/if}
									{:else}
										<span class="sl-cell-text">{formatCell(rawVal, col.fmt)}</span>
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	{#if sortedRows.length > pageSize}
		<div class="sl-table-footer">
			<span class="sl-page-info">
				Mostrando {startIdx + 1}–{Math.min(startIdx + pageSize, sortedRows.length)} de {nfInt.format(sortedRows.length)} registros
			</span>
			<div class="sl-page-btns">
				<button
					type="button"
					class="sl-page-btn"
					disabled={safePage <= 1}
					on:click={() => (currentPage = Math.max(1, safePage - 1))}
				>
					Anterior
				</button>
				<span class="sl-page-counter">{safePage} / {totalPages}</span>
				<button
					type="button"
					class="sl-page-btn"
					disabled={safePage >= totalPages}
					on:click={() => (currentPage = Math.min(totalPages, safePage + 1))}
				>
					Próxima
				</button>
			</div>
		</div>
	{/if}
</section>

<style>
	.sl-table-card {
		background: #0f141d;
		border: 1px solid #1e293b;
		border-radius: 10px;
		padding: 20px 22px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.sl-table-card.is-compact {
		height: 100%;
		justify-content: space-between;
	}

	.sl-table-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		flex-wrap: wrap;
	}

	.sl-table-heading {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.sl-table-controls {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	.sl-search-box {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		height: 34px;
		padding: 0 11px;
		border-radius: 6px;
		background: #141b26;
		border: 1px solid #334155;
		color: #94a3b8;
	}

	.sl-search-box input {
		background: transparent;
		border: none;
		outline: none;
		color: #f8fafc;
		font-size: 12.5px;
		width: 235px;
	}

	.sl-search-box input::placeholder {
		color: #64748b;
	}

	.sl-export-btn {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		height: 34px;
		padding: 0 12px;
		border-radius: 6px;
		background: #141b26;
		border: 1px solid #334155;
		color: #cbd5e1;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: border-color 0.15s ease, color 0.15s ease;
	}

	.sl-export-btn:hover {
		border-color: #475569;
		color: #f8fafc;
	}

	.sl-table-scroll {
		width: 100%;
		overflow-x: auto;
	}

	.sl-table {
		width: 100%;
		border-collapse: collapse;
		font-variant-numeric: tabular-nums;
	}

	.sl-table thead th {
		background: #141b26;
		color: #94a3b8;
		font-size: 10.5px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-align: left;
		padding: 0;
		border-bottom: 1px solid #1e293b;
		white-space: nowrap;
	}

	.sl-table thead th:first-child {
		border-radius: 6px 0 0 0;
	}

	.sl-table thead th:last-child {
		border-radius: 0 6px 0 0;
	}

	.sl-th-btn {
		width: 100%;
		padding: 10px 14px;
		background: transparent;
		border: none;
		color: inherit;
		font: inherit;
		text-transform: inherit;
		letter-spacing: inherit;
		display: inline-flex;
		align-items: center;
		gap: 5px;
		cursor: pointer;
	}

	.sl-table th.is-right .sl-th-btn {
		justify-content: flex-end;
	}

	.sl-table th.is-center .sl-th-btn {
		justify-content: center;
	}

	.sl-th-btn:hover,
	.sl-th-btn:focus-visible,
	.sl-table thead th.is-sorted {
		color: #e2e8f0;
		outline: none;
	}

	.sl-th-btn:focus-visible {
		box-shadow: inset 0 0 0 1px #3b82f6;
	}

	.sl-sort-arrow {
		color: #3b82f6;
		font-size: 10px;
	}

	.sl-table tbody tr {
		border-bottom: 1px solid #1e293b;
		transition: background 0.12s ease;
	}

	.sl-table tbody tr:last-child {
		border-bottom: none;
	}

	.sl-table tbody tr:hover {
		background: rgba(255, 255, 255, 0.02);
	}

	.sl-table tbody tr.is-leader td:first-child {
		box-shadow: inset 3px 0 0 #3b82f6;
	}

	.sl-table tbody td {
		padding: 13px 14px;
		color: #cbd5e1;
		font-size: 13px;
		vertical-align: middle;
		white-space: nowrap;
	}

	.sl-table th.is-right,
	.sl-table td.is-right {
		text-align: right;
	}

	.sl-table th.is-center,
	.sl-table td.is-center {
		text-align: center;
	}

	.sl-cell-rank {
		color: #94a3b8;
		font-weight: 600;
	}

	.sl-cell-rank.is-accent {
		color: #3b82f6;
	}

	.sl-cell-primary {
		color: #f8fafc;
		font-weight: 600;
	}

	.sl-cell-primary.is-accent {
		color: #3b82f6;
	}

	.sl-cell-text {
		color: #cbd5e1;
	}

	.sl-muted {
		color: #64748b;
	}

	.sl-bar-cell {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 5px;
		min-width: 84px;
	}

	.sl-bar-num {
		color: #f8fafc;
		font-size: 13px;
		font-weight: 600;
		line-height: 1;
	}

	.sl-bar-num.is-accent {
		color: #3b82f6;
	}

	.sl-bar-track {
		width: 84px;
		height: 4px;
		border-radius: 2px;
		background: #1e293b;
		overflow: hidden;
	}

	.sl-bar-fill {
		height: 100%;
		border-radius: 2px;
		background: #525866;
	}

	.sl-bar-fill.is-accent {
		background: #3b82f6;
	}

	.sl-growth-cell {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: #cbd5e1;
		font-weight: 500;
	}

	.sl-growth-cell.is-accent {
		color: #3b82f6;
		font-weight: 600;
	}

	.sl-tri {
		font-size: 9px;
		line-height: 1;
	}

	.sl-empty-cell {
		text-align: center;
		color: #94a3b8;
		padding: 28px 16px !important;
	}

	.sl-table-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding-top: 8px;
		border-top: 1px solid #1e293b;
		flex-wrap: wrap;
	}

	.sl-page-info {
		color: #94a3b8;
		font-size: 12px;
		font-variant-numeric: tabular-nums;
	}

	.sl-page-btns {
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}

	.sl-page-counter {
		color: #cbd5e1;
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		padding: 0 4px;
	}

	.sl-page-btn {
		height: 30px;
		padding: 0 11px;
		border-radius: 6px;
		background: #141b26;
		border: 1px solid #334155;
		color: #cbd5e1;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
	}

	.sl-page-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.sl-page-btn:not(:disabled):hover {
		border-color: #475569;
		color: #f8fafc;
	}
</style>
