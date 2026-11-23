<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout
	{data}
	title="SidraLake 360°"
	homePageName="Visão Executiva"
	neverShowQueries={true}
	fullWidth={true}
	hideTOC={true}
	builtWithEvidence={false}
	githubRepo="https://github.com/leoserpa/sidralake"
>
	<slot slot="content" />
</EvidenceDefaultLayout>
