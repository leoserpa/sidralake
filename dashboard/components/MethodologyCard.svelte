<script>
	let open = false;
</script>

<section class="sl-method-wrap">
	<button
		type="button"
		class="sl-method-toggle"
		aria-expanded={open}
		on:click={() => (open = !open)}
	>
		<span class="sl-method-title">
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<circle cx="12" cy="12" r="10" />
				<path d="M12 16v-4" />
				<path d="M12 8h.01" />
			</svg>
			<span>Metodologia &amp; Glossário Rápido — Score IMS, HHI, QL e Calendário IBGE</span>
		</span>
		<span class="sl-method-chevron" class:is-open={open} aria-hidden="true">▾</span>
	</button>

	{#if open}
		<div class="sl-method-grid">
			<div class="sl-method-item">
				<h4>Score IMS (0–100) &amp; Tiers</h4>
				<p>
					Índice composto de inteligência municipal ponderado em 4 pilares:
					<strong>Tamanho de Mercado (35%)</strong>, <strong>Poder de Compra (30%)</strong>,
					<strong>Dinamismo Real (20%)</strong> e <strong>Maturidade Empresarial (15%)</strong>.
					Tiers 1 a 4 agrupam de Polos Nacionais a Mercados Locais.
				</p>
			</div>
			<div class="sl-method-item">
				<h4>Deflação IPCA (Reais Constantes)</h4>
				<p>
					Todos os valores monetários (PIB Real, Massa Salarial e Salário Médio) são trazidos a
					preços constantes usando o índice oficial do <strong>IPCA (SIDRA 1737)</strong>,
					eliminando distorções inflacionárias nas comparações históricas e no CAGR 3A.
				</p>
			</div>
			<div class="sl-method-item">
				<h4>Diversificação (HHI) &amp; Especialização (QL)</h4>
				<p>
					<strong>HHI Div. (1 − HHI)</strong> mede o equilíbrio entre Agro, Indústria, Serviços e
					Adm. Pública (quanto maior, mais diversificada a economia). O <strong>Quociente Locacional (QL)</strong>
					compara o peso setorial de uma UF à média nacional (<code>QL ≥ 1,50</code> = Cluster Dominante).
				</p>
			</div>
			<div class="sl-method-item">
				<h4>Calendário Oficial de Publicação IBGE</h4>
				<p>
					Pesquisas conjunturais (<strong>IPCA, PMC, PMS e PNAD Contínua</strong>) atualizam
					mensal ou trimestralmente. Pesquisas estruturais municipais (<strong>PIB Municipal, VAB e CEMPRE</strong>)
					possuem defasagem oficial de 2–3 anos definida pelo próprio IBGE.
				</p>
			</div>
		</div>
	{/if}
</section>

<style>
	.sl-method-wrap {
		margin-top: 18px;
		background: #0b0f0d;
		border: 1px solid #2d3231;
		border-radius: 10px;
		overflow: hidden;
	}

	.sl-method-toggle {
		width: 100%;
		background: transparent;
		border: none;
		padding: 13px 18px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		color: #d4d8d6;
		font-size: 12.5px;
		font-weight: 600;
		cursor: pointer;
		text-align: left;
		transition: color 0.15s ease, background-color 0.15s ease;
	}

	.sl-method-toggle:hover {
		color: #f5f7f6;
		background: rgba(255, 255, 255, 0.02);
	}

	.sl-method-title {
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}

	.sl-method-title svg {
		color: #9ca3a0;
		flex-shrink: 0;
	}

	.sl-method-chevron {
		color: #9ca3a0;
		font-size: 14px;
		transition: transform 0.18s ease;
	}

	.sl-method-chevron.is-open {
		transform: rotate(180deg);
		color: #f5f7f6;
	}

	.sl-method-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 14px;
		padding: 4px 18px 18px 18px;
		border-top: 1px solid #1d2220;
	}

	.sl-method-item {
		padding: 12px 14px;
		background: #131716;
		border: 1px solid #232826;
		border-radius: 8px;
	}

	.sl-method-item h4 {
		margin: 0 0 6px 0;
		color: #f5f7f6;
		font-size: 12.5px;
		font-weight: 600;
	}

	.sl-method-item p {
		margin: 0;
		color: #9ca3a0;
		font-size: 12px;
		line-height: 1.5;
	}

	.sl-method-item strong {
		color: #d4d8d6;
		font-weight: 600;
	}

	.sl-method-item code {
		color: #60a5fa;
		font-size: 11.5px;
		background: rgba(59, 130, 246, 0.1);
		padding: 1px 5px;
		border-radius: 4px;
	}

	@media (max-width: 900px) {
		.sl-method-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
