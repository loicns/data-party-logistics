# SAM Makefile build — called by `sam build` for each Lambda function.
# SAM sets ARTIFACTS_DIR to the target build folder for each function.
# We copy only the Lambda source modules and install only Lambda dependencies.
# This keeps each package well under Lambda's 250 MB unzipped limit.

# `athena` ships the canonical CTAS .sql files so features_lambda can read them.
# `warehouse` ships the UN/LOCODE seed CSV that ais_stream/weather load at import
# to build port bounding boxes — without it the ingestion Lambdas FileNotFoundError.
LAMBDA_MODULES = serverless ingestion athena warehouse
LAMBDA_REQS    = requirements.txt

define _build
	cp -r $(LAMBDA_MODULES) $(ARTIFACTS_DIR)/
	# Force Linux arm64 wheels regardless of build host (macOS laptop or x86_64 CI):
	# pydantic ships a compiled core (pydantic_core) that must match the Lambda's
	# arm64 architecture, or the function fails with ImportModuleError at runtime.
	python3.12 -m pip install -r $(LAMBDA_REQS) -t $(ARTIFACTS_DIR) \
		--platform manylinux2014_aarch64 \
		--implementation cp \
		--python-version 3.12 \
		--only-binary=:all: \
		--upgrade --quiet
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

build-FeaturesFunction:
	$(call _build)

# Predict needs ML libs (lightgbm + scikit-learn) and only the serverless +
# models.features code — not the ingestion clients. Separate reqs keep the
# other functions lean.
build-PredictFunction:
	cp -r serverless models $(ARTIFACTS_DIR)/
	# lightgbm's lib_lightgbm.so links against libgomp (OpenMP), which the minimal
	# Lambda runtime doesn't ship. Vendor the Linux arm64 libgomp at the package
	# root — /var/task is on Lambda's LD_LIBRARY_PATH, so the loader finds it.
	cp vendor/lib/libgomp.so.1 $(ARTIFACTS_DIR)/
	# Native ML wheels (lightgbm/numpy) must be Linux arm64 to run on Lambda.
	# Fetch them cross-platform from a macOS host — no Docker needed.
	python3.12 -m pip install -r requirements-predict.txt -t $(ARTIFACTS_DIR) \
		--no-deps \
		--platform manylinux2014_aarch64 \
		--implementation cp \
		--python-version 3.12 \
		--only-binary=:all: \
		--upgrade --quiet
