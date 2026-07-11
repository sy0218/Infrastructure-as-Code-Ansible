#!/usr/bin/bash

set -euo pipefail # 에러/미정의변수/파이프실패 시 종료

log() {
    echo -e "\n$(date '+%Y-%m-%d %H:%M:%S') - $1\n"
}

run_cmd() {
    log "[RUN] $*"
    "$@"
}

log "===== START ansible setup ====="

run_cmd apt update
run_cmd apt install -y vim
run_cmd apt install -y ansible
run_cmd ansible --version

log "===== END ansible setup ====="
