# SAM Makefile build — called by `sam build` for each Lambda function.
# SAM sets ARTIFACTS_DIR to the target build folder for each function.
# We copy only the Lambda source modules and install only Lambda dependencies.
# This keeps each package well under Lambda's 250 MB unzipped limit.

LAMBDA_MODULES = serverless ingestion
LAMBDA_REQS    = requirements.txt

define _build
	cp -r $(LAMBDA_MODULES) $(ARTIFACTS_DIR)/
	python3.12 -m pip install -r $(LAMBDA_REQS) -t $(ARTIFACTS_DIR) --upgrade --quiet
endef

build-AisSnapshotFunction:
	$(call _build)

build-WeatherIngestionFunction:
	$(call _build)

build-NoaaIngestionFunction:
	$(call _build)

build-DashboardExportFunction:
	$(call _build)

build-FreshnessCheckFunction:
	$(call _build)
