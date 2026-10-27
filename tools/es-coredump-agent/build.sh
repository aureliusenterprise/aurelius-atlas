#!/usr/bin/env bash
# Build the coredump-filter javaagent (see the .java header).
set -euo pipefail
cd "$(dirname "$0")"
javac --release 17 -d classes CoredumpNoopAgent.java
jar --create --file coredump-noop.jar --manifest manifest.txt -C classes .
rm -rf classes
echo "built: $(pwd)/coredump-noop.jar"
