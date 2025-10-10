#!/bin/bash
set -e

: ${WALLET:?Please set WALLET env var}

POOL=${POOL:-asia.luckpool.net:3956}
PASSWORD=${PASSWORD:-x}
THREADS=${THREADS:-1}
WORKER=${WORKER:-render}

cd /opt/nheqminer/build
./nheqminer -v -l "$POOL" -u "${WALLET}.${WORKER}" -p "$PASSWORD" -t "$THREADS"
