"""
Upload local documents to S3 to prepare for Bedrock Knowledge Base ingestion.

Usage:
  python scripts/upload_to_s3_for_bedrock.py --bucket my-bucket --prefix bedrock/docs ./data/*.txt

The script uploads files under the given prefix and prints the S3 URIs.
"""
import boto3
import argparse
from pathlib import Path
import sys


def upload_files(bucket: str, prefix: str, paths):
    s3 = boto3.client("s3")
    uploaded = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"Skipping missing file: {p}")
            continue
        key = f"{prefix.rstrip('/')}/{path.name}"
        print(f"Uploading {path} -> s3://{bucket}/{key}")
        s3.upload_file(str(path), bucket, key)
        uploaded.append(f"s3://{bucket}/{key}")
    return uploaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="bedrock/docs")
    parser.add_argument("paths", nargs="+", help="Files to upload")
    args = parser.parse_args()
    if not args.paths:
        print("No files provided to upload")
        sys.exit(1)
    uploaded = upload_files(args.bucket, args.prefix, args.paths)
    print("Uploaded files:")
    for u in uploaded:
        print(u)


if __name__ == "__main__":
    main()
