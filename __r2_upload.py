#!/usr/bin/env python3
"""
Upload a large file to Cloudflare R2 via the S3-compatible API.
Designed for the Locahun3D sample PLY which exceeds the R2 web UI's
300 MB limit (boto3 handles multipart automatically).

Usage (interactive — keeps your secrets out of your shell history):
    python __r2_upload.py

Or with all args (for re-runs):
    python __r2_upload.py ^
        --endpoint  https://<ACCOUNT_ID>.r2.cloudflarestorage.com ^
        --bucket    locahun3d-samples ^
        --file      "F:\\UNDEFINED Dropbox\\...\\Kousaten_ForDemo_point_cloud.ply" ^
        --key       Kousaten_ForDemo_point_cloud.ply

Credentials can also be set via env vars (preferred):
    set R2_ACCESS_KEY_ID=...
    set R2_SECRET_ACCESS_KEY=...

Install once:
    pip install boto3
"""
import argparse, os, sys, time
from getpass import getpass

try:
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 is not installed. Run:")
    print("    pip install boto3")
    sys.exit(1)


def ask(prompt, default=None, secret=False):
    p = f"{prompt}" + (f" [{default}]" if default else "") + ": "
    fn = getpass if secret else input
    v = fn(p).strip()
    return v or default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--endpoint')
    ap.add_argument('--bucket')
    ap.add_argument('--file')
    ap.add_argument('--key')
    args = ap.parse_args()

    print("─" * 60)
    print("Cloudflare R2 upload — Locahun3D sample PLY")
    print("─" * 60)

    endpoint = args.endpoint or ask("R2 endpoint URL (https://<ID>.r2.cloudflarestorage.com)")
    bucket   = args.bucket   or ask("Bucket name", "locahun3d-samples")
    fpath    = args.file     or ask("Local file path (full path to the .ply)")
    if not os.path.isfile(fpath):
        sys.exit(f"ERROR: file not found: {fpath}")
    default_key = os.path.basename(fpath)
    key      = args.key      or ask("Key (filename in bucket)", default_key)

    ak = os.environ.get("R2_ACCESS_KEY_ID")
    sk = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not ak: ak = ask("Access Key ID")
    if not sk: sk = ask("Secret Access Key", secret=True)

    size_mb = os.path.getsize(fpath) / (1024 * 1024)
    print(f"\nReady to upload:")
    print(f"  file     : {fpath} ({size_mb:.1f} MB)")
    print(f"  bucket   : {bucket}")
    print(f"  key      : {key}")
    print(f"  endpoint : {endpoint}")
    if ask("Proceed? (y/N)", "N").lower() != "y":
        sys.exit("Aborted.")

    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name='auto',
        config=Config(
            signature_version='s3v4',
            retries={'max_attempts': 8, 'mode': 'standard'},
            # Allow long uploads to stay alive
            connect_timeout=30, read_timeout=120,
        ),
    )

    # Multipart upload: 32 MB parts → ~30 parallel parts for a ~900 MB file
    cfg = TransferConfig(
        multipart_threshold=64 * 1024 * 1024,
        multipart_chunksize=32 * 1024 * 1024,
        max_concurrency=4,
        use_threads=True,
    )

    start = time.time()
    last_pct = [-1]
    total = os.path.getsize(fpath)
    sent = [0]

    def progress(bytes_amount):
        sent[0] += bytes_amount
        pct = int(sent[0] / total * 100)
        if pct != last_pct[0]:
            elapsed = time.time() - start
            speed = sent[0] / elapsed / (1024 * 1024) if elapsed > 0 else 0
            print(f"\r  {pct:3d}%  {sent[0]/1024/1024:>7.1f} / {total/1024/1024:.1f} MB  ({speed:.1f} MB/s)", end="", flush=True)
            last_pct[0] = pct

    try:
        s3.upload_file(
            Filename=fpath, Bucket=bucket, Key=key,
            Config=cfg, Callback=progress,
            ExtraArgs={'ContentType': 'application/octet-stream'},
        )
        elapsed = time.time() - start
        print(f"\n\n✓ Upload complete in {elapsed:.1f}s ({size_mb/elapsed:.1f} MB/s avg)")
        print(f"\nObject URL (after enabling r2.dev public access):")
        print(f"  https://pub-<your-r2-hash>.r2.dev/{key}")
    except ClientError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
