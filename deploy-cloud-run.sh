#!/bin/bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-south1}"
SERVICE_NAME="${SERVICE_NAME:-yummydoors-backend}"
REPOSITORY="${REPOSITORY:-yummydoors-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID is required."
  echo "Example: PROJECT_ID=my-gcp-project ./deploy-cloud-run.sh"
  exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "========================================"
echo "   YUMMYDOORS CLOUD RUN DEPLOYMENT      "
echo "========================================"
echo "PROJECT: $PROJECT_ID"
echo "REGION:  $REGION"
echo "SERVICE: $SERVICE_NAME"
echo "IMAGE:   $IMAGE_URI"
echo "========================================"

gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker \
  --location="$REGION" \
  --description="YummyDoors backend Docker repository" \
  >/dev/null 2>&1 || true

gcloud auth configure-docker "${REGION}-docker.pkg.dev"

gcloud builds submit --tag "$IMAGE_URI" --region="$REGION"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

echo ""
echo "Deployment complete."
echo "Service URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/health"
