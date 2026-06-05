#!/usr/bin/env bash
# Pause all DPL ingestion to stop recurring AWS cost.
# Keeps every resource and ALL your S3 data intact — just stops the Lambdas
# from executing by pinning reserved concurrency to 0 (throttled = no cost).
#
# Reverse with: scripts/resume.sh
set -euo pipefail

REGION="eu-west-3"
export AWS_PROFILE="${AWS_PROFILE:-dpl}"

FUNCTIONS=(
  dpl-serverless-pilot-ais-snapshot
  dpl-serverless-pilot-weather
  dpl-serverless-pilot-noaa
  dpl-serverless-pilot-export
  dpl-serverless-pilot-freshness
)

echo "Pausing ${#FUNCTIONS[@]} Lambda functions (reserved concurrency = 0)..."
for fn in "${FUNCTIONS[@]}"; do
  aws lambda put-function-concurrency \
    --function-name "$fn" \
    --reserved-concurrent-executions 0 \
    --region "$REGION" >/dev/null
  echo "  paused: $fn"
done

echo
echo "Done. All ingestion is paused. Your S3 data is untouched."
echo "Residual cost is now ~\$0 (only a CloudWatch dashboard ~\$3/mo + pennies of S3 storage)."
echo "To stop the dashboard charge too, see SHUTDOWN.md 'Option B'."
echo "Resume anytime with: scripts/resume.sh"
