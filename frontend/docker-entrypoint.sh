#!/bin/sh
set -eu

source_modules=/opt/frontend-node-modules
mounted_modules=/workspace/frontend/node_modules

if ! cmp -s "$source_modules/.package-lock.sha256" "$mounted_modules/.package-lock.sha256"; then
    find "$mounted_modules" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a "$source_modules/." "$mounted_modules/"
fi

exec "$@"
