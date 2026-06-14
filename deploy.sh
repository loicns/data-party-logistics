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

# Load .env when present. CI can provide the same variables directly.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${AISSTREAM_API_KEY:?AISSTREAM_API_KEY is not set. Copy .env.example to .env or export it in the current shell.}"
export AWS_PROFILE="${AWS_PROFILE:-dpl}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
AIS_DURATION_SECONDS="${AIS_DURATION_SECONDS:-420}"
PUBLIC_DASHBOARD_BUCKET_NAME="${PUBLIC_DASHBOARD_BUCKET_NAME:-}"
PUBLIC_DASHBOARD_OBJECT_KEY="${PUBLIC_DASHBOARD_OBJECT_KEY:-demo-data.js}"
PUBLIC_DASHBOARD_DISTRIBUTION_ID="${PUBLIC_DASHBOARD_DISTRIBUTION_ID:-}"
PREDICTIONS_OBJECT_KEY="${PREDICTIONS_OBJECT_KEY:-predictions.json}"

PARAMETER_OVERRIDES=(
  "AisStreamApiKey=${AISSTREAM_API_KEY}"
  "AisDurationSeconds=${AIS_DURATION_SECONDS}"
  "PublicDashboardObjectKey=${PUBLIC_DASHBOARD_OBJECT_KEY}"
  "PredictionsObjectKey=${PREDICTIONS_OBJECT_KEY}"
)

if [[ -n "${ALERT_EMAIL}" ]]; then
  PARAMETER_OVERRIDES+=("AlertEmail=${ALERT_EMAIL}")
fi
if [[ -n "${PUBLIC_DASHBOARD_BUCKET_NAME}" ]]; then
  PARAMETER_OVERRIDES+=("PublicDashboardBucketName=${PUBLIC_DASHBOARD_BUCKET_NAME}")
fi
if [[ -n "${PUBLIC_DASHBOARD_DISTRIBUTION_ID}" ]]; then
  PARAMETER_OVERRIDES+=(
    "PublicDashboardDistributionId=${PUBLIC_DASHBOARD_DISTRIBUTION_ID}"
  )
fi

sam build
# Refuse to ship host-arch native wheels (the cause of the AIS outage).
scripts/check_wheel_arch.sh
sam deploy \
  --parameter-overrides "${PARAMETER_OVERRIDES[@]}" \
  "$@"
