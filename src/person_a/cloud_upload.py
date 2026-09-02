"""
cloud_upload.py - Upload merchant cohort baselines & transaction dataset into BigQuery.

Schema:
    Dataset: fraud_risk_manager
    Table: merchant_cohort_baselines & clean_transactions
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

PROCESSED_CSV = os.path.join(_PROJECT_ROOT, "data", "processed", "injected_transactions.csv")
BQ_DATASET = "fraud_risk_manager"
BQ_TABLE = "merchant_cohort_baselines"


def upload_to_bigquery():
    gcp_project_id = os.environ.get("GCP_PROJECT_ID")
    if not gcp_project_id:
        print("[cloud] [SKIPPED] GCP_PROJECT_ID not set in environment. Skipping BigQuery cloud upload.")
        return

    if not os.path.exists(PROCESSED_CSV):
        print(f"[cloud] [ERROR] CSV file not found at {PROCESSED_CSV}")
        return

    try:
        from google.cloud import bigquery
        from google.api_core.exceptions import NotFound

        client = bigquery.Client(project=gcp_project_id)
        dataset_ref = client.dataset(BQ_DATASET)
        try:
            client.get_dataset(dataset_ref)
            print(f"[cloud] Using BigQuery dataset: {BQ_DATASET}")
        except NotFound:
            print(f"[cloud] Creating BigQuery dataset: {BQ_DATASET}")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            client.create_dataset(dataset)

        table_id = f"{gcp_project_id}.{BQ_DATASET}.{BQ_TABLE}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition="WRITE_TRUNCATE",
        )

        print(f"[cloud] Uploading merchant cohort transactions to {table_id}...")
        with open(PROCESSED_CSV, "rb") as csv_file:
            load_job = client.load_table_from_file(csv_file, table_id, job_config=job_config)

        load_job.result()
        table = client.get_table(table_id)
        print(f"[cloud] [OK] Uploaded {table.num_rows:,} merchant transactions to BigQuery table {table_id}")

    except Exception as e:
        print(f"[cloud] [WARNING] BigQuery upload encountered an issue: {e}")


def main():
    upload_to_bigquery()


if __name__ == "__main__":
    main()
