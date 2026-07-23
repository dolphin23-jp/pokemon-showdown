#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess

CLIENT_SHA = "0e5715cc325796752d07e7ecd3fdd175ad8fc52b"


def replace_exact(source: str, old: str, new: str, expected: int = 1) -> str:
    count = source.count(old)
    if count != expected:
        raise RuntimeError(f"replacement count {count} != {expected}: {old[:100]!r}")
    return source.replace(old, new)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-root", required=True)
    parser.add_argument("--client-root", required=True)
    args = parser.parse_args()
    server = pathlib.Path(args.server_root).resolve()
    client = pathlib.Path(args.client_root).resolve()

    client_sha = subprocess.check_output(
        ["git", "-C", str(client), "rev-parse", "HEAD"], text=True
    ).strip()
    if client_sha != CLIENT_SHA:
        raise RuntimeError(f"Unexpected client SHA: {client_sha}")
    raw_date = subprocess.check_output(
        ["git", "-C", str(client), "show", "-s", "--format=%cI", "HEAD"], text=True
    ).strip()
    parsed_date = dt.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    commit_date = parsed_date.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    pin_path = server / "config/pokemon-showdown-client.json"
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    pin["commit"] = client_sha
    pin["commit_date"] = commit_date
    pin_path.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")

    battle_inventory_path = server / "docs/localization/phase-3-battle-text-inventory.json"
    battle_inventory = json.loads(battle_inventory_path.read_text(encoding="utf-8"))
    battle_inventory["generatedFromClientSha"] = client_sha
    battle_inventory_path.write_text(json.dumps(battle_inventory, indent=2) + "\n", encoding="utf-8")

    doc_path = server / "docs/localization/phase-3-t3-05-battle-chrome-apply.md"
    doc = doc_path.read_text(encoding="utf-8").replace("<强>", "<strong>").replace("</强>", "</strong>")
    doc_path.write_text(doc, encoding="utf-8")

    generator_path = server / "scripts/generate-phase3-ui-chrome-inventory.mjs"
    source = generator_path.read_text(encoding="utf-8")
    source = replace_exact(
        source,
        "\t{file: 'play.pokemonshowdown.com/src/panel-battle.tsx'},",
        "\t{\n\t\tfile: 'play.pokemonshowdown.com/src/panel-battle.tsx',\n"
        "\t\tappliedGroups: ['BattleChromeSources', 'SharedChromeSources'],\n\t},",
    )

    marker = (
        "function lineNumber(sourceFile, node) {\n"
        "\treturn sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;\n"
        "}\n"
    )
    insertion = marker + r'''

function readFrameworkGroups(clientRoot) {
	const filePath = path.join(clientRoot, 'play.pokemonshowdown.com/src/client-ui-ja-strings.ts');
	const source = fs.readFileSync(filePath, 'utf8');
	const sourceFile = ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
	const groups = new Map();
	for (const statement of sourceFile.statements) {
		if (!ts.isVariableStatement(statement)) continue;
		for (const declaration of statement.declarationList.declarations) {
			if (!ts.isIdentifier(declaration.name) || !declaration.name.text.endsWith('Sources')) continue;
			let initializer = declaration.initializer;
			if (initializer && ts.isAsExpression(initializer)) initializer = initializer.expression;
			if (!initializer || !ts.isObjectLiteralExpression(initializer)) {
				throw new Error(`${declaration.name.text} must be an object literal`);
			}
			const entries = new Map();
			for (const property of initializer.properties) {
				if (!ts.isPropertyAssignment(property) || !ts.isArrayLiteralExpression(property.initializer)) {
					throw new Error(`${declaration.name.text} must contain tuple property assignments`);
				}
				const [englishNode] = property.initializer.elements;
				if (!englishNode || !ts.isStringLiteral(englishNode)) {
					throw new Error(`${property.name.getText(sourceFile)} English source must be a string`);
				}
				entries.set(property.name.getText(sourceFile), englishNode.text);
			}
			groups.set(declaration.name.text, entries);
		}
	}
	return groups;
}

function appliedReference(node, target, groups) {
	if (!target.appliedGroups || !ts.isPropertyAccessExpression(node) || !ts.isIdentifier(node.expression)) {
		return null;
	}
	const groupName = node.expression.text.replace(/JA$/, 'Sources');
	if (!target.appliedGroups.includes(groupName)) return null;
	const group = groups.get(groupName);
	if (!group) throw new Error(`Missing UI chrome group ${groupName}`);
	const english = group.get(node.name.text);
	if (!english) throw new Error(`Unknown UI chrome reference ${node.expression.text}.${node.name.text}`);
	return english;
}

function appliedReferenceType(node, sourceFile) {
	let current = node.parent;
	while (current && !ts.isSourceFile(current)) {
		if (ts.isJsxAttribute(current)) return jsxAttributeName(current);
		if (ts.isPropertyAssignment(current)) {
			const key = current.name.getText(sourceFile).replace(/^['"]|['"]$/g, '');
			if (key === 'title' || key === 'body') {
				let ancestor = current.parent;
				while (ancestor && !ts.isCallExpression(ancestor) && !ts.isSourceFile(ancestor)) {
					ancestor = ancestor.parent;
				}
				if (ancestor && ts.isCallExpression(ancestor) && ts.isPropertyAccessExpression(ancestor.expression) &&
					ancestor.expression.name.text === 'notify') return 'notify';
			}
		}
		current = current.parent;
	}
	return 'label';
}
'''
    source = replace_exact(source, marker, insertion)
    source = replace_exact(
        source,
        "function collectFile(clientRoot, target, fileIndex) {",
        "function collectFile(clientRoot, target, fileIndex, groups) {",
    )
    source = replace_exact(
        source,
        "\tfunction visit(node) {\n\t\tif (ts.isJsxText(node)) {",
        "\tfunction visit(node) {\n"
        "\t\tconst english = appliedReference(node, target, groups);\n"
        "\t\tif (english !== null) addEntry(node, appliedReferenceType(node, sourceFile), english);\n"
        "\t\tif (ts.isJsxText(node)) {",
    )
    source = replace_exact(
        source,
        "\tconst clientRoot = resolveClientRoot(args.serverRoot, args.clientRoot);\n"
        "\tconst entries = TARGETS.flatMap((target, index) => collectFile(clientRoot, target, index));",
        "\tconst clientRoot = resolveClientRoot(args.serverRoot, args.clientRoot);\n"
        "\tconst groups = readFrameworkGroups(clientRoot);\n"
        "\tconst entries = TARGETS.flatMap((target, index) => collectFile(clientRoot, target, index, groups));",
    )
    source = replace_exact(
        source,
        "This inventory contains hard-coded English UI chrome from the Phase 3 battle and Teambuilder scope.",
        "This inventory contains Phase 3 battle and Teambuilder UI chrome, including applied framework references and remaining hard-coded English strings.",
    )
    source = replace_exact(
        source,
        "\t\t'| File:line | Type | Current English string |',",
        "\t\t'| File:line | Type | English source string |',",
    )
    generator_path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
