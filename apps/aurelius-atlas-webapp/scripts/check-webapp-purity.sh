#!/usr/bin/env bash
# Purity gate for the Aurelius Atlas webapp port (WBP-02, SHL-01, SHL-09, SHL-10, UIC-07; layers DD-869/DD-870).
#
# The port is a rewrite in Angular idiom, not a transplant (ADR 053). This
# script fails if a forbidden legacy construct enters the tree: NgModules and
# the legacy bootstrap, Aurelius-lib imports, the custom state-management
# stack, ngx-translate, the environment.ts pattern, or a service that owns
# state in a bare BehaviorSubject (signals are the state primitive).
#
# It greps the webapp *and* the Angular libraries the webapp builds from
# source (DD-131, DD-137), so ported code cannot carry a construct the app
# itself is banned from.
#
# It also enforces the search feature's layer boundaries (the rule DD-869 named
# and 7.44/DD-870 makes enforceable): a feature never imports a sibling
# feature, and the shared layers never import a feature. Code two features need
# lives in `shared/` (or `meta/`), not in one of the features.
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

# --- search layer boundaries (DD-869's rule, enforced by DD-870) ------------
#
# `search/` is layered: the features (browse, details, editor, results) sit
# above the shared layers (shared, meta). A feature may read down into a
# shared layer, and a shared layer may read no feature at all — never sideways
# into a sibling feature. When two features need the same code, it moves to a
# shared layer instead of being imported across (7.44 moved the four helpers
# this rule caught).
search="apps/aurelius-atlas-webapp/src/app/search"
features=(browse details editor results)
shared_layers=(shared meta)

# "<importing dir>|the import it must not make"
layer_checks=()
for src in "${features[@]}"; do
    for dst in "${features[@]}"; do
        [ "$src" = "$dst" ] || layer_checks+=("$src|$dst")
    done
done
for src in "${shared_layers[@]}"; do
    for dst in "${features[@]}"; do
        layer_checks+=("$src|$dst")
    done
done

for pair in "${layer_checks[@]}"; do
    src="${pair%%|*}"
    dst="${pair##*|}"
    # Any relative import that climbs to `search/` and back down into the
    # sibling feature: ../<dst>/, ../../<dst>/, and so on.
    if matches=$(grep -rn --include='*.ts' -E "from \"(\.\./)+${dst}/" "$search/$src" 2>/dev/null); then
        echo "FAIL: layer boundary — search/$src imports search/$dst (a shared layer never imports a feature; a feature never imports a sibling: DD-869, DD-870)"
        echo "$matches"
        status=1
    fi
done

# --- the lineage feature is reached through its barrel (DD-884) --------------
#
# Lineage is a top-level feature (promoted out of `search/details/lineage/`
# because it reaches into `shell/` and `tokens`). `search/` mounts the lineage
# box and reads its store, and it does so through the feature's `index.ts` —
# `from "../../lineage"`, never a deep file import. That keeps the box's
# internals (the diagram, the tabs, the AR3 parsers, the routed quickview) off
# the surface another feature can lean on. The routed quickview stays a direct
# file import, but in `routes.ts`, which is outside `search/` (DD-884's
# code-split note) — so this guard's scope is exactly `search/`.
lineage_re='from "(\.\./)+lineage/'
if matches=$(grep -rn --include='*.ts' -E "$lineage_re" "$search" 2>/dev/null); then
    echo "FAIL: lineage boundary — search/ imports a file inside the lineage feature instead of its barrel (../lineage): DD-884"
    echo "$matches"
    status=1
fi

if [ "$status" -eq 0 ]; then
    echo "webapp purity check passed (WBP-02, SHL-01, SHL-09, SHL-10, UIC-07; search layers DD-869/DD-870, lineage barrel DD-884)."
fi
exit "$status"
