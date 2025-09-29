#!/usr/bin/env bash
set -euo pipefail

# Cloud Run deploy helper for Ask & See
#
# Usage:
#   ./deploy.sh --project YOUR_PROJECT --region us-central1 [--repo apps] [--image ask-and-see] [--with-gcs]
#
# Notes:
# - Reads GOOGLE_API_KEY, GENERATOR_MODEL, CHROMA_DIR from .env if present.
# - If --with-gcs is set, mounts a GCS bucket at /data and sets CHROMA_DIR=/data/chroma.

PROJECT=""
REGION="us-central1"
REPO="apps"
IMAGE="ask-and-see"
WITH_GCS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --with-gcs) WITH_GCS="true"; shift 1 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Locate gcloud (PATH or common local SDK path)
if command -v gcloud >/dev/null 2>&1; then
  GCLOUD="gcloud"
elif [ -x "$HOME/google-cloud-sdk/bin/gcloud" ]; then
  GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
elif [ -x "/Users/$(whoami)/Documents/google-cloud-sdk/bin/gcloud" ]; then
  GCLOUD="/Users/$(whoami)/Documents/google-cloud-sdk/bin/gcloud"
else
  echo "gcloud not found. Install Google Cloud SDK, then run: gcloud auth login" >&2
  exit 1
fi

if [[ -z "${PROJECT}" ]]; then
  PROJECT=$($GCLOUD config get-value project 2>/dev/null || true)
fi
if [[ -z "${PROJECT}" ]]; then
  echo "--project is required (or set a default with: gcloud config set project PROJECT_ID)" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env if present (export all variables defined there)
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -o allexport
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +o allexport
fi

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "GOOGLE_API_KEY is not set. Add it to $ROOT_DIR/.env or export it before running." >&2
  exit 1
fi

GENERATOR_MODEL="${GENERATOR_MODEL:-gemma-2-2b-it}"
CHROMA_DIR_VAL="${CHROMA_DIR:-.chroma}"

echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Repo:    $REPO"
echo "Image:   $IMAGE"
echo "Model:   $GENERATOR_MODEL"
echo "Persist: ${WITH_GCS} (CHROMA_DIR=${CHROMA_DIR_VAL})"

$GCLOUD services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project "$PROJECT"

# Create Artifact Registry if needed
$GCLOUD artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="App images" \
  --project "$PROJECT" || true

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:latest"

# Build & push
$GCLOUD builds submit "$ROOT_DIR" --tag "$IMAGE_URI" --project "$PROJECT"

DEPLOY_ARGS=(
  --image "$IMAGE_URI"
  --region "$REGION"
  --platform managed
  --allow-unauthenticated
  --project "$PROJECT"
)

if [[ "$WITH_GCS" == "true" ]]; then
  BUCKET="ask-and-see-chroma-$PROJECT"
  gsutil mb -l "$REGION" "gs://$BUCKET" || true
  DEPLOY_ARGS+=(
    --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY,GENERATOR_MODEL=$GENERATOR_MODEL,CHROMA_DIR=/data/chroma"
    --add-volume "name=vecstore,type=gcs,bucket=$BUCKET"
    --mount "path=/data,volume=vecstore"
  )
else
  DEPLOY_ARGS+=(
    --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY,GENERATOR_MODEL=$GENERATOR_MODEL,CHROMA_DIR=$CHROMA_DIR_VAL"
  )
fi

$GCLOUD run deploy "$IMAGE" "${DEPLOY_ARGS[@]}"

URL=$($GCLOUD run services describe "$IMAGE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')
echo "Deployed: $URL"
echo "Open: $URL/spa"


