# Deploying to staging

`.github/workflows/deploy-staging.yml` runs after CI passes on `main` (or by hand from the Actions tab). It builds three images, runs migrations as a Cloud Run Job, then deploys the web service and the pipeline job. GitHub signs in to GCP with workload identity federation, so there are no JSON keys anywhere.

Until the repository variables below exist, the workflow skips with a notice and CI stays green.

## One-time GCP setup (staging)

Run in Cloud Shell as a project owner. Replace the values in the first block.

```bash
PROJECT=arrakis-staging
REGION=asia-south1
REPO=Suneel2903/Arrakis-Realty          # GitHub owner/repo
SQL=arrakis-staging-pg                  # Cloud SQL instance name
gcloud config set project $PROJECT
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')

gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com iamcredentials.googleapis.com

# Images
gcloud artifacts repositories create arrakis --repository-format=docker --location=$REGION

# Database: Postgres 16 (PostGIS is an extension, enabled by migration 0001)
gcloud sql instances create $SQL --database-version=POSTGRES_16 --region=$REGION \
  --tier=db-custom-1-3840 --storage-auto-increase
gcloud sql databases create arrakis --instance=$SQL
DB_PASS=$(openssl rand -base64 24 | tr -d '/+=')
gcloud sql users create arrakis --instance=$SQL --password="$DB_PASS"
SOCK=/cloudsql/$PROJECT:$REGION:$SQL

# Two connection strings, because dbmate and the postgres.js client name the socket differently
printf 'postgres://arrakis:%s@localhost/arrakis?host=%s' "$DB_PASS" "$SOCK" | \
  gcloud secrets create DATABASE_URL --data-file=-
printf 'postgres://arrakis:%s@/arrakis?socket=%s' "$DB_PASS" "$SOCK" | \
  gcloud secrets create MIGRATE_DATABASE_URL --data-file=-

# Service accounts: one for GitHub to deploy, one the services run as
gcloud iam service-accounts create gh-deploy --display-name="GitHub deploy"
gcloud iam service-accounts create arrakis-run --display-name="Arrakis runtime"
DEPLOY_SA=gh-deploy@$PROJECT.iam.gserviceaccount.com
RUN_SA=arrakis-run@$PROJECT.iam.gserviceaccount.com
for r in roles/run.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$DEPLOY_SA --role=$r
done
gcloud iam service-accounts add-iam-policy-binding $RUN_SA \
  --member=serviceAccount:$DEPLOY_SA --role=roles/iam.serviceAccountUser
for r in roles/cloudsql.client roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$RUN_SA --role=$r
done

# Workload identity federation, limited to this repository
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github --location=global \
  --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository \
  --attribute-condition="assertion.repository == '$REPO'"
gcloud iam service-accounts add-iam-policy-binding $DEPLOY_SA \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"

echo "GCP_WIF_PROVIDER=projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github"
```

## GitHub repository variables

Settings → Secrets and variables → Actions → **Variables** (not secrets; none of these are sensitive):

| Variable | Example |
|---|---|
| `GCP_PROJECT_ID` | `arrakis-staging` |
| `GCP_WIF_PROVIDER` | printed by the last command above |
| `GCP_DEPLOY_SA` | `gh-deploy@arrakis-staging.iam.gserviceaccount.com` |
| `GCP_RUNTIME_SA` | `arrakis-run@arrakis-staging.iam.gserviceaccount.com` |
| `GCP_AR_REPO` | `arrakis` |
| `GCP_CLOUDSQL_INSTANCE` | `arrakis-staging:asia-south1:arrakis-staging-pg` |

Then re-run **Deploy staging** from the Actions tab. The web URL is printed by the "Deploy web" step. Check `<url>/api/health`.

## Later (not in S00)

Cloud Scheduler trigger for `rera-pipeline`, Cloud CDN and the tiles bucket, the prod project with PITR backups.
