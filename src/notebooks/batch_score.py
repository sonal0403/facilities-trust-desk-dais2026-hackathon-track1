"""
Batch scoring script for Facility Trust Desk.

Reads all facilities from the source Delta table, scores each one across
all 6 capabilities, and writes results to workspace.default.facility_trust_scores.

Run this on Databricks (serverless or cluster) or locally with databricks-connect.
"""

import sys
import json
from datetime import datetime, timezone

# When running on Databricks, adjust path to find the scoring module
# Assumes the project is uploaded to workspace files
sys.path.insert(0, "/Workspace/Users/sonal.0403@gmail.com/facility-trust-desk")

from scoring.engine import score_facility_all_capabilities
from scoring.keywords import CAPABILITY_KEYWORDS

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
SOURCE_TABLE = "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities"
TARGET_TABLE = "workspace.default.facility_trust_scores"

FIELDS_TO_READ = [
    "unique_id",
    "capability",
    "procedure",
    "equipment",
    "specialties",
    "description",
]


def run_batch_scoring(spark):
    """Main batch scoring logic."""

    print(f"[{datetime.now()}] Reading facilities from {SOURCE_TABLE}...")
    df = spark.table(SOURCE_TABLE).select(*FIELDS_TO_READ)
    facilities = df.collect()
    print(f"[{datetime.now()}] Loaded {len(facilities)} facilities.")

    scored_at = datetime.now(timezone.utc).isoformat()
    results = []

    for i, row in enumerate(facilities):
        facility_id = row["unique_id"]
        if not facility_id:
            continue

        texts = {
            "capability": row["capability"] or "",
            "procedure": row["procedure"] or "",
            "equipment": row["equipment"] or "",
            "specialties": row["specialties"] or "",
            "description": row["description"] or "",
        }

        scores = score_facility_all_capabilities(texts)

        for capability, result in scores.items():
            results.append({
                "facility_id": facility_id,
                "capability": capability,
                "trust_level": result["trust_level"],
                "evidence_citations": json.dumps(result["evidence_citations"]),
                "fields_matched": json.dumps(result["fields_matched"]),
                "match_count": result["match_count"],
                "scored_at": scored_at,
            })

        if (i + 1) % 1000 == 0:
            print(f"[{datetime.now()}] Scored {i + 1}/{len(facilities)} facilities...")

    print(f"[{datetime.now()}] Scoring complete. Total rows: {len(results)}")

    # Write to Delta
    print(f"[{datetime.now()}] Writing to {TARGET_TABLE}...")
    results_df = spark.createDataFrame(results)
    results_df.write.mode("overwrite").saveAsTable(TARGET_TABLE)

    print(f"[{datetime.now()}] Done. Table {TARGET_TABLE} written with {len(results)} rows.")

    # Quick validation
    print("\n--- Trust Level Distribution ---")
    spark.sql(f"""
        SELECT capability, trust_level, COUNT(*) as cnt
        FROM {TARGET_TABLE}
        GROUP BY capability, trust_level
        ORDER BY capability, trust_level
    """).show(50, truncate=False)


# -------------------------------------------------------------------
# Entry point — works in Databricks notebook (spark is global)
# or can be called from a local script with databricks-connect
# -------------------------------------------------------------------
if __name__ == "__main__":
    # When running as a Databricks notebook, `spark` is already available
    try:
        spark  # noqa: F821
    except NameError:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()

    run_batch_scoring(spark)
