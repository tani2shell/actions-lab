#!/bin/sh
set -eu
cd "$(dirname "$0")"
LOCAL_FLAG="FLAG{alx_local_$(openssl rand -hex 8)}"
PROOF_FLAG="FLAG{alx_proof_$(openssl rand -hex 8)}"
RUNNER_TOKEN="rt_$(openssl rand -hex 16)"
cat > .env <<EOF
LOCAL_FLAG=$LOCAL_FLAG
PROOF_FLAG=$PROOF_FLAG
RUNNER_TOKEN=$RUNNER_TOKEN
EOF
chmod 600 .env
echo "$LOCAL_FLAG" > ../actions-lab-local.flag
echo "$PROOF_FLAG" > ../actions-lab-proof.flag
chmod 600 ../actions-lab-local.flag ../actions-lab-proof.flag
echo seeded; wc -c ../actions-lab-local.flag ../actions-lab-proof.flag
