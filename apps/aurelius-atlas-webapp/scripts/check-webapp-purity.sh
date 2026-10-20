#!/usr/bin/env bash
# Purity gate for the Aurelius Atlas webapp port (WBP-02, SHL-01, SHL-09, SHL-10, UIC-07).
#
# The port is a rewrite in Angular idiom, not a transplant (ADR 053). This
# script fails if a forbidden legacy construct enters the tree: NgModules and
# the legacy bootstrap, Aurelius-lib imports, the custom state-management
# stack, ngx-translate, the environment.ts pattern, or a service that owns
# state in a bare BehaviorSubject (signals are the state primitive).
#
# It greps the webapp *and* the Angular libraries the webapp builds from
# source (DD-042, DD-048), so ported code cannot carry a construct the app
# itself is banned from.
#
# Patterns match *usage* (imports, decorators, directives, `new`), so prose in
# comments/docs that names a forbidden construct as context is allowed.
set -euo pipefail

# Workspace root: this script lives in apps/aurelius-atlas-webapp/scripts.
cd "$(dirname "$0")/../../.."

# Trees the gate covers. Only `src` dirs: the webapp's own scripts/ and the
# vendored fixtures legitimately name the forbidden constructs (this script's
# pattern list, the legacy dictionaries).
roots=(
    "apps/aurelius-atlas-webapp/src"
)
for lib in libs/angular/*/src; do
    [ -d "$lib" ] && roots+=("$lib")
done

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
    for root in "${roots[@]}"; do
        if matches=$(grep -rn --include='*.ts' --include='*.html' -E "$pattern" "$root" 2>/dev/null); then
            echo "FAIL: forbidden construct — $label"
            echo "$matches"
            status=1
        fi
    done
done

if [ "$status" -eq 0 ]; then
    echo "webapp purity check passed (WBP-02, SHL-01, SHL-09, SHL-10, UIC-07)."
fi
exit "$status"
