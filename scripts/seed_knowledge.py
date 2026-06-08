#!/usr/bin/env python3
"""
seed_knowledge.py — Upload company knowledge base documents to S3.

Each agent reads from its own prefix in the S3 bucket:
  hr/        → AVA reads these
  finance/   → FELIX reads these
  advisor/   → ATLAS reads these
  shared/    → All agents read these

Run manually:
    python scripts/seed_knowledge.py
    python scripts/seed_knowledge.py --bucket my-bucket-name --docs-dir ./docs
"""

import argparse
import boto3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BUCKET = os.getenv("KNOWLEDGE_BUCKET", "")
REGION = os.getenv("AWS_REGION", "us-east-1")
PROFILE = os.getenv("AWS_PROFILE", "default")

# Map local folder names to S3 prefixes
FOLDER_PREFIX_MAP = {
    "hr":      "hr/",
    "finance": "finance/",
    "advisor": "advisor/",
    "shared":  "shared/",
}

def upload_docs(bucket: str, docs_dir: str):
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    s3 = session.client("s3")
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        print(f"Docs directory not found: {docs_path}")
        sys.exit(1)

    uploaded = 0
    for folder, prefix in FOLDER_PREFIX_MAP.items():
        folder_path = docs_path / folder
        if not folder_path.exists():
            print(f"  Skipping {folder}/ (not found)")
            continue
        for file in folder_path.glob("*.md"):
            key = f"{prefix}{file.name}"
            s3.upload_file(str(file), bucket, key)
            print(f"  ✓ Uploaded {file.name} → s3://{bucket}/{key}")
            uploaded += 1

    # Also upload any .md files directly in docs/ to shared/
    for file in docs_path.glob("*.md"):
        key = f"shared/{file.name}"
        s3.upload_file(str(file), bucket, key)
        print(f"  ✓ Uploaded {file.name} → s3://{bucket}/{key}")
        uploaded += 1

    print(f"\nTotal: {uploaded} files uploaded to s3://{bucket}/")


def main():
    parser = argparse.ArgumentParser(description="Seed BSSE knowledge base to S3")
    parser.add_argument("--bucket",   default=BUCKET,       help="S3 bucket name")
    parser.add_argument("--docs-dir", default="./docs",     help="Path to docs directory")
    args = parser.parse_args()

    if not args.bucket:
        print("Error: --bucket is required (or set KNOWLEDGE_BUCKET in .env)")
        sys.exit(1)

    print(f"Uploading knowledge base to s3://{args.bucket}/")
    upload_docs(args.bucket, args.docs_dir)


if __name__ == "__main__":
    main()
