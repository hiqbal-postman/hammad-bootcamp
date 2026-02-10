#!/usr/bin/env python3
"""
TechCorp API Ingestion Script
Exports (or reads) an OpenAPI spec and syncs it to Postman Spec Hub.

Usage (AWS export mode):
    export POSTMAN_API_KEY="PMAK-..."
    python ingest_from_apigw.py \
        --workspace-id "<workspace-id>" \
        --region "us-east-1" \
        --rest-api-id "yvzmor0d68" \
        --stage-name "dev" \
        --spec-name "TechCorp Payments API (Spec Hub)"

Usage (local spec mode):
    export POSTMAN_API_KEY="PMAK-..."
    python ingest_from_apigw.py \
        --workspace-id "<workspace-id>" \
        --local-spec openapi.yaml \
        --spec-name "TechCorp Payments API (Spec Hub)"
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


POSTMAN_API_BASE = "https://api.getpostman.com"


def http_json(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    """Make an HTTP request and return JSON response."""
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"HTTP {e.code} calling {url}: {raw}") from e


def aws_export_openapi(region: str, rest_api_id: str, stage_name: str, out_path: str) -> None:
    """Export OpenAPI 3.0 spec from AWS API Gateway."""
    cmd = [
        "aws",
        "apigateway",
        "get-export",
        "--region",
        region,
        "--rest-api-id",
        rest_api_id,
        "--stage-name",
        stage_name,
        "--export-type",
        "oas30",
        out_path,
    ]
    print(f"[..] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def list_specs(workspace_id: str, api_key: str) -> list[dict]:
    """List all specs in a workspace."""
    url = f"{POSTMAN_API_BASE}/specs?workspaceId={workspace_id}"
    resp = http_json("GET", url, api_key)
    return resp.get("specs", [])


def _extract_spec_id(resp: dict) -> str:
    """Extract spec ID from various response shapes."""
    if "spec" in resp and isinstance(resp["spec"], dict) and "id" in resp["spec"]:
        return resp["spec"]["id"]
    if "id" in resp and isinstance(resp["id"], str):
        return resp["id"]
    raise RuntimeError(f"Unexpected spec response: {resp}")


def create_spec(workspace_id: str, api_key: str, name: str, spec_yaml: str) -> str:
    """Create a new spec in Spec Hub."""
    url = f"{POSTMAN_API_BASE}/specs?workspaceId={workspace_id}"
    payload_variants = [
        # Variant A (common in examples)
        {"name": name, "type": "openapi3", "language": "yaml", "schema": spec_yaml},
        # Variant B (seen in some Postman request templates)
        {"specName": name, "specType": "openapi3", "filePath": f"{name}.yaml", "content": spec_yaml},
        # Variant C (wrapped)
        {"spec": {"name": name, "type": "openapi3", "language": "yaml", "schema": spec_yaml}},
    ]

    last_err = None
    for body in payload_variants:
        try:
            resp = http_json("POST", url, api_key, body=body)
            return _extract_spec_id(resp)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to create spec (tried {len(payload_variants)} payloads): {last_err}") from last_err


def update_spec(spec_id: str, api_key: str, name: str, spec_yaml: str) -> None:
    """Update an existing spec in Spec Hub."""
    url = f"{POSTMAN_API_BASE}/specs/{spec_id}"
    payload_variants = [
        {"name": name, "type": "openapi3", "language": "yaml", "schema": spec_yaml},
        {"specName": name, "specType": "openapi3", "filePath": f"{name}.yaml", "content": spec_yaml},
        {"spec": {"name": name, "type": "openapi3", "language": "yaml", "schema": spec_yaml}},
    ]
    last_err = None
    for body in payload_variants:
        try:
            http_json("PUT", url, api_key, body=body)
            return
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to update spec {spec_id}: {last_err}") from last_err


def generate_collection_from_spec(spec_id: str, api_key: str) -> dict:
    """Trigger collection generation from a spec."""
    url = f"{POSTMAN_API_BASE}/specs/{spec_id}/generations/collection"
    return http_json("POST", url, api_key, body={})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export OpenAPI from API Gateway and sync to Postman Spec Hub"
    )
    parser.add_argument("--workspace-id", required=True, help="Postman workspace ID")
    parser.add_argument(
        "--local-spec",
        help="Path to a local OpenAPI spec to ingest (skips API Gateway export)",
    )
    parser.add_argument("--region", help="AWS region (e.g., us-east-1)")
    parser.add_argument("--rest-api-id", help="API Gateway REST API ID")
    parser.add_argument("--stage-name", help="API Gateway stage (e.g., dev)")
    parser.add_argument(
        "--spec-name",
        default="TechCorp Payments API (Spec Hub)",
        help="Name for the spec in Spec Hub",
    )
    parser.add_argument("--out", default="openapi.yaml", help="Output file (written in both modes)")
    args = parser.parse_args()

    api_key = os.environ.get("POSTMAN_API_KEY")
    if not api_key:
        print("❌ Missing POSTMAN_API_KEY environment variable", file=sys.stderr)
        return 2

    # Step 1: Get spec (AWS export OR local fallback)
    print("=" * 60)
    if args.local_spec:
        print("Step 1: Load OpenAPI from local file")
        print("=" * 60)
        with open(args.local_spec, "r", encoding="utf-8") as f:
            spec_yaml = f.read()
        if args.local_spec != args.out:
            with open(args.out, "w", encoding="utf-8") as out:
                out.write(spec_yaml)
        print(f"✅ Loaded spec → {args.local_spec} ({len(spec_yaml)} chars)")
        if args.local_spec != args.out:
            print(f"✅ Wrote copy → {args.out}")
    else:
        print("Step 1: Export OpenAPI from API Gateway")
        print("=" * 60)
        missing = [
            name
            for name, val in [
                ("--region", args.region),
                ("--rest-api-id", args.rest_api_id),
                ("--stage-name", args.stage_name),
            ]
            if not val
        ]
        if missing:
            parser.error(
                "Missing required arguments for AWS export mode: "
                + ", ".join(missing)
                + " (or provide --local-spec)"
            )

        aws_export_openapi(args.region, args.rest_api_id, args.stage_name, args.out)
        with open(args.out, "r", encoding="utf-8") as f:
            spec_yaml = f.read()
        print(f"✅ Exported spec → {args.out} ({len(spec_yaml)} chars)")

    # Step 2: Upsert to Spec Hub
    print("\n" + "=" * 60)
    print("Step 2: Upsert spec to Postman Spec Hub")
    print("=" * 60)
    existing = [s for s in list_specs(args.workspace_id, api_key) if s.get("name") == args.spec_name]
    if existing and existing[0].get("id"):
        spec_id = existing[0]["id"]
        update_spec(spec_id, api_key, args.spec_name, spec_yaml)
        print(f"✅ Updated spec: {args.spec_name} (id={spec_id})")
    else:
        spec_id = create_spec(args.workspace_id, api_key, args.spec_name, spec_yaml)
        print(f"✅ Created spec: {args.spec_name} (id={spec_id})")

    # Step 3: Generate baseline collection
    print("\n" + "=" * 60)
    print("Step 3: Generate baseline collection from spec")
    print("=" * 60)
    gen = generate_collection_from_spec(spec_id, api_key)
    print(f"✅ Generation request completed (response keys: {sorted(gen.keys())})")

    print("\n" + "=" * 60)
    print("✅ DONE - Ingestion complete")
    print("=" * 60)
    print("Next: Protect curated collections from regen drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
