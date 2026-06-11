#!/usr/bin/env bash
# Deploy the DPL SAM stack.
#
# The AISStream secret is read from .env (the single source of truth) and
# injected at deploy time, so it never has to live in samconfig.toml or git.
# Non-secret parameters are listed here so the whole deploy is one command.
#
# Usage:
#   ./deploy.sh                 # build + deploy
#   ./deploy.sh --no-confirm-changeset   # extra args pass through to `sam deploy`
set -euo pipefail

cd "$(dirname "$0")"

# Load .env (AISSTREAM_API_KEY, etc.) into the environment.
set -a
# shellcheck disable=SC1091
source .env
set +a

: "${AISSTREAM_API_KEY:?AISSTREAM_API_KEY is not set in .env}"
export AWS_PROFILE="${AWS_PROFILE:-dpl}"

sam build
# Refuse to ship host-arch native wheels (the cause of the AIS outage).
scripts/check_wheel_arch.sh
sam deploy \
  --parameter-overrides \
    "AlertEmail=nsabiyeloic@gmail.com" \
    "AisStreamApiKey=${AISSTREAM_API_KEY}" \
    "AisDurationSeconds=300" \
    "PublicDashboardBucketName=dpl-dashboard-861276086413" \
    "PublicDashboardObjectKey=demo-data.js" \
    "PublicDashboardDistributionId=E2UUM6WQAEKJW2" \
    "PredictionsObjectKey=predictions.json" \
  "$@"
