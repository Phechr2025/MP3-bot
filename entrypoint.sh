#!/bin/bash
set -e

: ${WALLET:?Please set WALLET env var (your VRSC address)}

POOL=${POOL:-asia.luckpool.net:3956}
PASSWORD=${PASSWORD:-x,d=1024}
THREADS=${THREADS:-1}

cd /opt/VerusCoinMiner
./install.sh <<EOF
$WALLET
$POOL
$PASSWORD
$THREADS
EOF

tail -f /dev/null
