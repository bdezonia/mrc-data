#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
g++ -O3 -std=c++17 -DNDEBUG -march=native -flto -o mrc_fast_transform mrc_fast_transform.cpp
printf 'Built: %s/mrc_fast_transform\n' "$PWD"
