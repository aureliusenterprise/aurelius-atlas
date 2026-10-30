#!/usr/bin/env bash
# Regenerates ../aurelius_atlas_dsl/generated from Atlas's grammar with the ANTLR tool (DD-240).
# The tool's version must equal antlr4-python3-runtime's in ../pyproject.toml. Needs Java 11 or later.
set -euo pipefail

version=4.13.2
sha256=eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76
jar="${XDG_CACHE_HOME:-$HOME/.cache}/antlr/antlr4-${version}-complete.jar"

cd "$(dirname "$0")"
if [[ ! -f "$jar" ]]; then
    mkdir -p "$(dirname "$jar")"
    curl -sSfL -o "$jar" "https://repo1.maven.org/maven2/org/antlr/antlr4/${version}/antlr4-${version}-complete.jar"
fi
echo "${sha256}  ${jar}" | sha256sum --check --quiet

out=../aurelius_atlas_dsl/generated
java -jar "$jar" -Dlanguage=Python3 -no-visitor -no-listener -Xexact-output-dir -o "$out" AtlasDSLLexer.g4 AtlasDSLParser.g4
rm -f "$out"/*.interp "$out"/*.tokens
