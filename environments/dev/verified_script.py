#!/usr/bin/env python3
"""
IAM Access‑Key Inventory

* Lists every IAM user in the account.
* Retrieves all access keys for each user.
* Flags any ACTIVE key that is >= 90 days old.
* Emits a CSV report to stdout (or optionally to S3).

Author:  Your Name
Date:    2026‑06‑17
"""

from __future__ import annotations

import argparse
import csv
import sys
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Tuple, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

# ----------------------------------------------------------------------
# Global constants (tweak via CLI)
# ----------------------------------------------------------------------
DEFAULT_AGE_DAYS = 90
DEFAULT_MAX_WORKERS = 10
DEFAULT_REGION = "us-east-1"          # IAM is global, but we need a region for the client.
S3_UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB (only used if you enable S3 output)

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def isoformat(dt_obj: dt.datetime) -> str:
    """Return a UTC ISO‑8601 string without microseconds."""
    return dt_obj.replace(tzinfo=dt.timezone.utc).isoformat(timespec="seconds") + "Z"


def days_old(created: dt.datetime) -> int:
    """Number of whole days between now (UTC) and a creation timestamp."""
    now = dt.datetime.now(dt.timezone.utc)
    delta = now - created
    return delta.days


def validate_permissions(iam_client: boto3.client) -> None:
    """
    Perform a cheap dry‑run to ensure the caller has the required IAM permissions.
    Raises an exception if the call fails with AccessDenied.
    """
    try:
        iam_client.list_users(MaxItems=1)
        iam_client.list_access_keys(UserName="non‑existent‑user", MaxItems=1)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "AccessDenied":
            raise PermissionError("IAM permissions missing: need ListUsers & ListAccessKeys") from exc
        # If the user truly does not exist we get NoSuchEntity – that’s fine.
    except BotoCoreError as exc:
        raise RuntimeError("Unable to validate IAM permissions") from exc


def list_all_users(iam_client: boto3.client) -> List[Dict[str, Any]]:
    """Return a list of all IAM users (full dicts as returned by list_users)."""
    paginator = iam_client.get_paginator("list_users")
    users: List[Dict[str, Any]] = []
    for page in paginator.paginate():
        users.extend(page.get("Users", []))
    return users


def fetch_user_keys(
    iam_client: boto3.client,
    user_name: str,
) -> List[Dict[str, Any]]:
    """Return a list of access‑key dicts for the given user."""
    paginator = iam_client.get_paginator("list_access_keys")
    keys: List[Dict[str, Any]] = []
    for page in paginator.paginate(UserName=user_name):
        keys.extend(page.get("AccessKeyMetadata", []))
    return keys


def process_user(
    iam_client: boto3.client,
    user: Dict[str, Any],
    age_threshold: int,
) -> List[Tuple]:
    """
    For a single IAM user, return a list of rows (tuples) for every key.
    Each row matches the CSV column order defined in `output_header`.
    """
    rows: List[Tuple] = []
    user_name = user["UserName"]
    user_created = user["CreateDate"]

    try:
        keys = fetch_user_keys(iam_client, user_name)
    except ClientError as exc:
        # Log and skip the user – a single failing call shouldn't abort the whole audit.
        print(f"[WARN] Could not list keys for user {user_name}: {exc}", file=sys.stderr)
        return rows

    for key in keys:
        key_id = key["AccessKeyId"]
        status = key["Status"]            # Active / Inactive
        created = key["CreateDate"]
        age = days_old(created)

        is_stale = (status == "Active" and age >= age_threshold)

        rows.append((
            user_name,
            isoformat(user_created),
            key_id,
            status,
            isoformat(created),
            age,
            "YES" if is_stale else "NO",
        ))
    return rows


def write_csv(
    rows: List[Tuple],
    header: Tuple[str, ...],
    outfile: Any,
) -> None:
    """Write rows (list of tuples) as CSV using the supplied header."""
    writer = csv.writer(outfile)
    writer.writerow(header)
    writer.writerows(rows)


def upload_to_s3(
    s3_client: boto3.client,
    bucket: str,
    key: str,
    data: bytes,
) -> None:
    """Upload the CSV bytes to the given S3 location."""
    s3_client.put_object(Bucket=bucket, Key=key, Body=data)
    print(f"[INFO] Uploaded report to s3://{bucket}/{key}")


# ----------------------------------------------------------------------
# Main function (CLI entry point)
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory all IAM access keys and flag any active keys older than a threshold."
    )
    parser.add_argument(
        "--age-days",
        type=int,
        default=DEFAULT_AGE_DAYS,
        help=f"Age in days beyond which an ACTIVE key is considered stale (default: {DEFAULT_AGE_DAYS})",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Number of threads for parallel per‑user calls (default: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the CSV report to a local file instead of stdout.",
    )
    parser.add_argument(
        "--s3-bucket",
        type=str,
        default=None,
        help="If supplied, also upload the CSV to this S3 bucket (key will be generated automatically).",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=DEFAULT_REGION,
        help="AWS region to use for the (global) IAM client – defaults to us-east-1.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Optional named boto3 profile to use.",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Boto3 session / clients (with sensible retry config)
    # ------------------------------------------------------------------
    session_kwargs = {"region_name": args.region}
    if args.profile:
        session_kwargs["profile_name"] = args.profile
    session = boto3.Session(**session_kwargs)

    # Enable exponential back‑off retries (default 5 retries, 0.5‑20 s).
    retry_cfg = Config(
        retries=dict(
            max_attempts=10,
            mode="standard",
        )
    )
    iam = session.client("iam", config=retry_cfg)

    # Validate we have the needed permissions before doing heavy work.
    try:
        validate_permissions(iam)
    except PermissionError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Gather data
    # ------------------------------------------------------------------
    print("[INFO] Enumerating IAM users …", file=sys.stderr)
    users = list_all_users(iam)
    print(f"[INFO] Found {len(users)} users.", file=sys.stderr)

    header = (
        "UserName",
        "UserCreateDate",
        "AccessKeyId",
        "KeyStatus",
        "KeyCreateDate",
        "KeyAgeDays",
        "Stale(>=90d)_Active",
    )
    all_rows: List[Tuple] = []

    # Use a thread pool to fetch keys for many users in parallel.
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_user = {
            executor.submit(process_user, iam, user, args.age_days): user["UserName"]
            for user in users
        }

        for future in as_completed(future_to_user):
            user_name = future_to_user[future]
            try:
                rows = future.result()
                all_rows.extend(rows)
            except Exception as exc:  # pragma: no cover – defensive
                print(f"[ERROR] Unexpected error processing {user_name}: {exc}", file=sys.stderr)

    # Sort for deterministic output (optional but nice)
    all_rows.sort(key=lambda r: (r[0], r[2]))   # UserName, AccessKeyId

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    if args.output:
        out_fh = args.output.open("w", newline="", encoding="utf-8")
        close_after = True
    else:
        out_fh = sys.stdout
        close_after = False

    write_csv(all_rows, header, out_fh)

    if close_after:
        out_fh.close()
        print(f"[INFO] Report written to {args.output}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Optional S3 upload
    # ------------------------------------------------------------------
    if args.s3_bucket:
        s3 = session.client("s3", config=retry_cfg)
        # Build a deterministic S3 key using the current timestamp
        ts = dt.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        s3_key = f"iam-key-inventory-{ts}.csv"

        # Convert CSV to bytes (fast in‑memory)
        from io import BytesIO, StringIO

        buf = StringIO()
        write_csv(all_rows, header, buf)
        csv_bytes = buf.getvalue().encode("utf-8")
        upload_to_s3(s3, args.s3_bucket, s3_key, csv_bytes)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_keys = len(all_rows)
    stale_keys = sum(1 for r in all_rows if r[6] == "YES")
    print(
        f"[SUMMARY] Processed {len(users)} users, {total_keys} keys total, {stale_keys} stale (>= {args.age_days}d) active keys.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()