#!/usr/bin/env bash
# Resume all DPL ingestion after a pause.
# Removes the reserved-concurrency=0 cap so the hourly schedules run again.
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

echo "Resuming ${#FUNCTIONS[@]} Lambda functions..."
for fn in "${FUNCTIONS[@]}"; do
  aws lambda delete-function-concurrency \
    --function-name "$fn" \
    --region "$REGION" >/dev/null
  echo "  resumed: $fn"
done

echo
echo "Done. The hourly schedules will collect data again from the next tick."
echo "Verify with one manual run:"
echo "  aws lambda invoke --function-name dpl-serverless-pilot-ais-snapshot \\"
echo "    --region $REGION --payload '{\"duration_seconds\": 60}' \\"
echo "    --cli-binary-format raw-in-base64-out /tmp/ais_out.json && cat /tmp/ais_out.json"
