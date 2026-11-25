<script>
	import { onDestroy } from 'svelte';

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

	$: row = rows[0] ?? null;
	$: parts = [
		row?.ipca_ref ? `IPCA ${row.ipca_ref}` : null,
		row?.pnad_ref ? `PNAD ${row.pnad_ref}` : null,
		row?.pib_ano ? `PIB ${row.pib_ano}` : null,
		row?.pop_ano ? `Pop. ${row.pop_ano}` : null
	].filter(Boolean);
</script>

<footer class="sl-footer">
	<span>
		<strong>Fonte dos Dados:</strong> Instituto Brasileiro de Geografia e Estatística (IBGE) · Dados públicos abertos · Defasagens entre séries seguem o calendário oficial de divulgação do IBGE.
	</span>
	{#if parts.length > 0}
		<span class="sl-footer-freshness">Competências oficiais: {parts.join(' · ')}</span>
	{/if}
	<span>SidraLake 360° · GNU GPL v3.0</span>
</footer>

<style>
	.sl-footer-freshness {
		color: #9ca3a0;
		font-variant-numeric: tabular-nums;
	}
</style>
