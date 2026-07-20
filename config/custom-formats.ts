// Personal formats for the private Pokemon Showdown AI server.

export const Formats: import('../sim/dex-formats').FormatList = [
	{
		section: "Personal AI Formats",
		column: 1,
	},
	{
		name: "[Gen 9] National Dex All Generations BSS",
		desc: `All official Pok&eacute;mon, moves, items, and abilities from every generation under Generation 9 battle mechanics. Bring six Pok&eacute;mon and pick three.`,
		mod: 'gen9',
		searchShow: false,
		bestOfDefault: true,
		debug: true,
		ruleset: [
			'NatDex Mod',
			'Team Preview',
			'Max Team Size = 6',
			'Max Move Count = 4',
			'Picked Team Size = 3',
			'!! Adjust Level = 50',
			'HP Percentage Mod',
			'Cancel Mod',
			'Endless Battle Clause',
		],
	},
];
