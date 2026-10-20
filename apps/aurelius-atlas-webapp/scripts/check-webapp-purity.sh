#!/usr/bin/env bash
# Purity gate for the Aurelius Atlas webapp port (WBP-02, SHL-01, SHL-09, SHL-10).
#
# The port is a rewrite in Angular idiom, not a transplant (ADR 053). This
# script fails if a forbidden legacy construct enters the tree: NgModules and
# the legacy bootstrap, Aurelius-lib imports, the custom state-management
# stack, ngx-translate, the environment.ts pattern, or a service that owns
# state in a bare BehaviorSubject (signals are the state primitive).
#
# Patterns match *usage* (imports, decorators, directives, `new`), so prose in
# comments/docs that names a forbidden construct as context is allowed.
set -euo pipefail

cd "$(dirname "$0")/.."

# Each entry: "<pattern>|<what it is>"
checks=(
    "@NgModule|NgModule (use standalone components, SHL-01)"
    "platformBrowserDynamic|legacy bootstrap (use bootstrapApplication, SHL-01)"
    "@models4insight/|Aurelius platform libs (not dependencies of this workspace)"
    "from ['\"][^'\"]*ngx-translate|ngx-translate (use @angular/localize, SHL-09)"
    "ngx-translate.*\.forRoot|ngx-translate module import (SHL-09)"
    "from ['\"][^'\"]*environment|environment.ts pattern (use /config.json + AppConfig, SHL-10)"
    "new BehaviorSubject|state-owning BehaviorSubject (use signals; RxJS interop only, SHL-01)"
)

status=0
for check in "${checks[@]}"; do
    pattern="${check%%|*}"
    label="${check#*|}"
    if matches=$(grep -rn --include='*.ts' --include='*.html' -E "$pattern" src/ 2>/dev/null); then
        echo "FAIL: forbidden construct — $label"
        echo "$matches"
        status=1
    fi
done

if [ "$status" -eq 0 ]; then
    echo "webapp purity check passed (WBP-02, SHL-01, SHL-09, SHL-10)."
fi
exit "$status"
