#!/usr/bin/env python3
"""aggregate_data.py — Data Aggregation Engine for arXiv Technical Report.

Aggregates crawl measurements and metrics from all 4 team members across multiple
accounts and runs in `input/` into standardized files in `book/data/`.

Handles:
  - Root finalized runs (single/latest report.zip per run)
  - Checkpoint-only runs (multiple incremental batches per run)
  - Deduplication of papers by `arxiv_id` (ensuring 20,000 unique papers)
  - Deduplication of versions by `(arxiv_id, version)`
  - Deduplication of references by `(arxiv_id, reference_arxiv_id)`
  - Safe type handling (arxiv_id as string, null handling)
  - Comprehensive summary metrics and multi-run benchmark compilation

Usage:
  python scripts/aggregate_data.py [--source PATH] [--target PATH] [--build]
"""

import argparse
import csv
import io
import math
import os
import re
import tempfile
import statistics
import warnings
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any, Optional

MEMBER_DISPLAY = {
    "danh": "Danh",
    "khang": "Khang",
    "khanh": "Khánh",
    "nguyen": "Nguyên",
}


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_report_archive(path: Path, run_id: str, kind: str = "report") -> Dict[str, Any]:
    """Match an input report ZIP to its adjacent crawler completion receipt."""
    receipt_path = path.with_name("backup_receipt.json")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        entry = receipt["archives"][kind]
        expected_hash = entry["sha256"]
        expected_bytes = entry["bytes"]
        if (receipt["run_id"] != run_id or entry["filename"] != path.name
                or type(expected_bytes) is not int or expected_bytes < 0
                or not isinstance(expected_hash, str) or len(expected_hash) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in expected_hash)):
            raise ValueError("Invalid report receipt identity or digest fields")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Missing or invalid backup receipt for {path}") from exc
    if path.stat().st_size != expected_bytes:
        raise ValueError(f"Report ZIP byte count differs from receipt: {path}")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash.lower():
        raise ValueError(f"Report ZIP SHA-256 differs from receipt: {path}")
    return {"receipt_path": str(receipt_path), "bytes": expected_bytes,
            "sha256": actual_hash, "verified": True, "kind": kind}


def find_default_source() -> Path:
    """Locate the input directory in standard locations."""
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root.parent / "input",
        repo_root / "input",
        Path.cwd().parent / "input",
        Path.cwd() / "input",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return repo_root.parent / "input"


def get_member_display(member_dir_name: str) -> str:
    """Normalize member name for reporting."""
    low = member_dir_name.lower().strip()
    return MEMBER_DISPLAY.get(low, member_dir_name.capitalize())


def collect_runs(source_dir: Path) -> List[Dict[str, Any]]:
    """Discover all runs across members and accounts, separating root runs and checkpoint runs."""
    discovered = []

    for member_dir in sorted(source_dir.iterdir()):
        if not member_dir.is_dir() or member_dir.name.startswith("."):
            continue
        member_name = get_member_display(member_dir.name)

        for acc_dir in sorted(member_dir.iterdir()):
            if not acc_dir.is_dir() or not acc_dir.name.startswith("acc"):
                continue
            account_name = acc_dir.name

            m1_dir = acc_dir / "Milestone1"
            if not m1_dir.is_dir():
                continue

            root_runs = {
                d.name: d
                for d in m1_dir.iterdir()
                if d.is_dir() and len(d.name) == 36 and "-" in d.name
            }

            cp_dir = m1_dir / "checkpoints"
            cp_runs = (
                {d.name: d for d in cp_dir.iterdir() if d.is_dir()}
                if cp_dir.is_dir()
                else {}
            )

            # 1. Process Root Runs (Finalized complete runs)
            for run_id, run_path in sorted(root_runs.items()):
                zips = list(run_path.rglob("report.zip"))
                if not zips:
                    continue
                # Pick largest/latest report.zip
                zips.sort(key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
                discovered.append({
                    "run_id": run_id,
                    "member": member_name,
                    "account": account_name,
                    "is_checkpoint": False,
                    "zip_paths": [zips[0]],
                    "base_path": run_path,
                })

            # 2. Process Checkpoint-Only Runs (Incremental batches)
            for run_id, run_path in sorted(cp_runs.items()):
                if run_id in root_runs:
                    # Skip checkpoint if root run already exists (root is consolidated)
                    continue

                batch_zips = []
                for ts_dir in sorted(run_path.iterdir()):
                    if ts_dir.is_dir():
                        rz = ts_dir / "report.zip"
                        if rz.is_file():
                            batch_zips.append(rz)

                if batch_zips:
                    discovered.append({
                        "run_id": run_id,
                        "member": member_name,
                        "account": account_name,
                        "is_checkpoint": True,
                        "zip_paths": batch_zips,
                        "base_path": run_path,
                    })

    return discovered


def safe_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number != number.to_integral_value():
            raise ValueError(f"Expected nonnegative integer, got {value!r}")
        return int(number)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid integer: {value!r}") from exc


def safe_float(value):
    if value is None or value == "":
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid nonnegative measurement: {value!r}")
    return number


def canonical_arxiv_id(value):
    value = re.sub(r"v[1-9][0-9]*$", "", str(value or "").strip())
    if value and not re.fullmatch(r"(?:[0-9]{4}\.[0-9]{4,5}|[A-Za-z][A-Za-z0-9.-]*/[0-9]{7})", value):
        raise ValueError(f"Invalid arXiv ID: {value!r}")
    return value


def assignment_coverage(papers, assignment_path=None):
    path = Path(assignment_path) if assignment_path else Path(__file__).resolve().parents[1] / "config/assignments.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 1:
        raise ValueError("Unsupported assignment manifest")
    expected = {}
    for row in spec["ranges"]:
        month, end = row["start_month"], row["end_month"]
        while month <= end:
            lo = row["start_id"] if month == row["start_month"] else 1
            hi = row["end_id"] if month == end else spec["month_end_ids"][month]
            if not 1 <= lo <= hi <= 99999:
                raise ValueError("Invalid assignment range")
            for number in range(lo, hi + 1):
                identifier = month[2:4] + month[5:7] + f".{number:05d}"
                if identifier in expected:
                    raise ValueError(f"Overlapping assignment: {identifier}")
                expected[identifier] = row["member"]
            year, number = map(int, month.split("-"))
            month = f"{year + (number == 12):04d}-{number % 12 + 1:02d}"
    if not expected:
        raise ValueError("Empty assignment manifest")
    actual = set(papers)
    resolved = {pid for pid, paper in papers.items() if str(paper.get("title") or "").strip()
                and str(paper.get("submission_date") or "").strip()}
    return {
        "id_discovery_coverage": len(set(expected) & resolved) / len(expected),
        "assigned_ids_target": len(expected),
        "missing_assigned_ids_count": len(set(expected) - actual),
        "unexpected_ids_count": len(actual - set(expected)),
        "invalid_assigned_metadata_count": len((set(expected) & actual) - resolved),
        "wrong_member_ids_count": sum(papers[pid]["member"] != expected[pid] for pid in actual & set(expected)),
        "assignment_manifest_sha256": sha256_file(path),
        "assigned_member_targets": dict(Counter(expected.values())),
    }


def parse_csv_from_zip(z, filename, required=False, columns=()):
    if filename not in z.namelist():
        if required:
            raise ValueError(f"Missing required {filename} in {z.filename}")
        return []
    reader = csv.DictReader(io.StringIO(z.read(filename).decode("utf-8")), strict=True)
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not set(columns) <= set(headers):
        raise ValueError(f"Invalid columns for {filename}: {headers}")
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Malformed CSV rows in {filename}")
    return rows


def parse_json_from_zip(z, filename, required=False):
    if filename not in z.namelist():
        if required:
            raise ValueError(f"Missing required {filename} in {z.filename}")
        return None
    value = json.loads(z.read(filename).decode("utf-8"))
    return value


def aggregate_corpus(source_dir, target_dir, assignment_path=None):
    """Build a complete snapshot off-target; roll back ordinary publication failures.

    The directory swap is not a lock for concurrent writers/readers. Run ingestion
    before Book builds; an interrupted publication retains its sibling backup.
    """
    target = Path(target_dir).absolute()
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError("Target must be a real directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}-stage-", dir=target.parent) as work:
        staged = Path(work) / "snapshot"
        result = _aggregate_corpus(Path(source_dir), staged, assignment_path)
        # Keep the backup outside TemporaryDirectory so an interrupted swap does
        # not destroy the previous snapshot during cleanup.
        backup = target.with_name(f".{target.name}-previous")
        if backup.exists():
            raise ValueError(f"Recover or remove previous interrupted snapshot first: {backup}")
        had_target = target.exists()
        if had_target:
            os.replace(target, backup)
        try:
            os.replace(staged, target)
        except BaseException:
            if had_target:
                os.replace(backup, target)
            raise
        if had_target:
            try:
                shutil.rmtree(backup)
            except OSError:
                warnings.warn(f"Snapshot published; old backup requires cleanup: {backup}", RuntimeWarning)
        return result


def _aggregate_corpus(source_dir, target_dir, assignment_path=None):
    """Validate and materialize an unpublished snapshot."""
    print(f"[INFO] Scanning runs from {source_dir}...")
    run_configs = collect_runs(source_dir)
    print(f"[INFO] Discovered {len(run_configs)} total run entries.")

    if not run_configs:
        raise ValueError("No report runs discovered; refusing to replace existing data")
    if len({item["run_id"] for item in run_configs}) != len(run_configs):
        raise ValueError("Duplicate run ID across member/account directories")

    # Validate every selected checkpoint/final archive before replacing any data.
    # A checksum calculated without comparison is not verification.
    verified_archives = {
        path: verify_report_archive(path, item["run_id"])
        for item in run_configs for path in item["zip_paths"]
    }
    target_dir.mkdir(parents=True, exist_ok=True)

    papers_dict: Dict[str, Dict[str, Any]] = {}
    versions_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    references_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    references_by_paper = {}
    resource_samples: List[Dict[str, Any]] = []
    benchmark_runs: List[Dict[str, Any]] = []
    run_metadata: List[Dict[str, Any]] = []

    status_priority = {"success": 4, "no_tex": 3, "failed": 2, "pending": 1}
    ref_priority = {"success": 4, "partial": 3, "not_found": 2, "failed": 1, "pending": 0, "unknown": 0}

    processed_zip_count = 0

    for item in run_configs:
        run_id = item["run_id"]
        member = item["member"]
        account = item["account"]
        is_cp = item["is_checkpoint"]
        zip_paths = item["zip_paths"]

        run_papers_count = 0
        run_discovery_seconds = 0.0
        run_bench_entry = None

        for zpath in zip_paths:
            processed_zip_count += 1
            try:
                with zipfile.ZipFile(zpath, "r") as z:
                    manifest = parse_json_from_zip(z, "manifest.json", required=True)
                    if not isinstance(manifest, dict) or manifest.get("run_id") != run_id or not isinstance(manifest.get("papers"), dict):
                        raise ValueError("Manifest schema/run ID mismatch")
                    papers_csv_rows = parse_csv_from_zip(z, "papers.csv", required=True, columns=("arxiv_id", "versions_expected", "reference_status", "total_references", "kept_references"))
                    versions_csv_rows = parse_csv_from_zip(z, "versions.csv", required=True, columns=("arxiv_id", "version", "status"))
                    all_refs_rows = parse_csv_from_zip(z, "references_all.csv", columns=("arxiv_id", "reference_arxiv_id"))
                    refs_csv_rows = (parse_csv_from_zip(z, "references.csv", columns=("arxiv_id", "reference_arxiv_id"))
                                     if "references.csv" in z.namelist() else all_refs_rows)
                    observed_counts = Counter(row["arxiv_id"] for row in all_refs_rows)
                    bench_data = parse_json_from_zip(z, "benchmark.json", required=True)
                    if not isinstance(bench_data, dict) or ("run_id" in bench_data and bench_data["run_id"] != run_id):
                        raise ValueError("Benchmark schema/run ID mismatch")
                    if bench_data.get("cpu_only") is not None and type(bench_data["cpu_only"]) is not bool:
                        raise ValueError("cpu_only must be boolean or null")
                    for key in ("wall_seconds", "ram_peak_bytes", "ram_mean_bytes", "disk_peak_bytes", "final_disk_bytes"):
                        bench_data[key] = safe_float(bench_data.get(key))
                    for row in papers_csv_rows + versions_csv_rows + refs_csv_rows + all_refs_rows:
                        if row.get("run_id") and row["run_id"] != run_id:
                            raise ValueError("CSV run ID mismatch")

                    # Handle discovery time
                    if manifest and "discovery" in manifest:
                        disc = manifest["discovery"]
                        disc_sec = disc.get("elapsed_seconds")
                        if disc_sec and isinstance(disc_sec, (int, float)):
                            run_discovery_seconds = max(run_discovery_seconds, float(disc_sec))

                    # 1. Process Papers
                    # Build lookup from papers.csv rows
                    p_csv_lookup = {r["arxiv_id"]: r for r in papers_csv_rows}
                    if len(p_csv_lookup) != len(papers_csv_rows) or set(p_csv_lookup) != set(manifest["papers"]):
                        raise ValueError("Duplicate IDs or manifest/papers.csv ID mismatch")

                    manifest_papers = manifest.get("papers", {}) if manifest else {}

                    # Union of all arxiv_ids in this zip
                    all_pids = set(manifest_papers.keys()) | set(p_csv_lookup.keys())
                    for pid in sorted(all_pids):
                        pid_str = canonical_arxiv_id(pid)
                        if not pid_str:
                            continue

                        p_info = manifest_papers.get(pid_str, {})
                        rec = p_info.get("record", {}) if isinstance(p_info, dict) else {}
                        meta = rec.get("metadata", {}) if isinstance(rec, dict) else {}
                        csv_info = p_csv_lookup.get(pid_str, {})

                        title = meta.get("title") or csv_info.get("title") or ""
                        submission_date = meta.get("submission_date") or csv_info.get("submission_date") or ""

                        # Missing timings remain unknown; malformed values reject ingestion.
                        elapsed_sec = safe_float(csv_info.get("elapsed_seconds") or p_info.get("elapsed_seconds"))

                        v_exp = safe_int(csv_info.get("versions_expected"), default=None)
                        if v_exp is None or v_exp < 1:
                            raise ValueError(f"Missing/invalid expected versions for {pid_str}")
                        record_versions = rec.get("versions", [])
                        if record_versions:
                            v_exp = max(v_exp, max(safe_int(v) for v in record_versions))
                        v_suc = safe_int(csv_info.get("versions_success"), default=0)
                        v_notex = safe_int(csv_info.get("versions_no_tex"), default=0)
                        v_fail = safe_int(csv_info.get("versions_failed"), default=0)
                        v_pend = safe_int(csv_info.get("versions_pending"), default=0)

                        raw_t_refs = csv_info.get("total_references")
                        if raw_t_refs is None or raw_t_refs == "":
                            t_refs = None
                        else:
                            t_refs = safe_int(raw_t_refs, default=None)

                        k_refs = safe_int(csv_info.get("kept_references"), default=0)
                        inc_refs = safe_int(csv_info.get("incomplete_references"), default=None)

                        source_status = csv_info.get("source_status") or "unknown"
                        ref_status = csv_info.get("reference_status") or "unknown"
                        if ref_status not in ref_priority:
                            raise ValueError(f"Invalid reference status: {ref_status}")
                        ref_result = p_info.get("references") or {}
                        if not isinstance(ref_result, dict):
                            raise ValueError("Invalid reference result")
                        if ref_result.get("pagination_complete") is False or ref_status in ("failed", "not_found", "pending", "unknown"):
                            t_refs = None
                        observed_refs = t_refs
                        if isinstance(ref_result.get("all_references"), list):
                            observed_refs = len(ref_result["all_references"])
                        if "references_all.csv" in z.namelist():
                            observed_refs = observed_counts[pid_str]
                        if t_refs is not None and observed_refs is not None and t_refs != observed_refs:
                            raise ValueError(f"Reference total/store mismatch for {pid_str}")
                        if observed_refs is not None and observed_refs < k_refs:
                            raise ValueError(f"Observed reference count below kept for {pid_str}")
                        if inc_refs is not None and inc_refs > k_refs:
                            raise ValueError(f"Incomplete reference count exceeds kept for {pid_str}")

                        paper_record = {
                            "arxiv_id": pid_str,
                            "member": member,
                            "account": account,
                            "run_id": run_id,
                            "title": title,
                            "submission_date": submission_date,
                            "metadata_source": csv_info.get("metadata_source") or manifest.get("metadata_source"),
                            "elapsed_seconds": elapsed_sec,
                            "source_status": source_status,
                            "reference_status": ref_status,
                            "versions_expected": v_exp,
                            "versions_success": v_suc,
                            "versions_no_tex": v_notex,
                            "versions_failed": v_fail,
                            "versions_pending": v_pend,
                            "total_references": t_refs,
                            "observed_reference_rows": observed_refs,
                            "_metadata": meta,
                            "_reference_snapshot": (run_id, str(zpath)),
                            "kept_references": k_refs,
                            "incomplete_references": inc_refs,
                        }

                        # Deduplicate: if exists, keep the one with higher success/more complete info
                        if pid_str not in papers_dict:
                            papers_dict[pid_str] = paper_record
                            run_papers_count += 1
                        else:
                            existing = papers_dict[pid_str]
                            if existing["member"] != member:
                                raise ValueError(f"Paper assigned to multiple members: {pid_str}")
                            existing["versions_expected"] = max(existing["versions_expected"], v_exp)
                            cur_r_prio = ref_priority.get(existing.get("reference_status"), 0)
                            new_r_prio = ref_priority.get(ref_status, 0)
                            if (new_r_prio > cur_r_prio) or (
                                new_r_prio == cur_r_prio and (k_refs > (existing.get("kept_references") or 0))
                            ):
                                existing["reference_status"] = ref_status
                                existing["total_references"] = t_refs
                                existing["kept_references"] = k_refs
                                existing["incomplete_references"] = inc_refs
                                existing["run_id"] = run_id
                                existing["account"] = account
                                existing["observed_reference_rows"] = observed_refs
                                existing["_reference_snapshot"] = (run_id, str(zpath))

                            if not existing.get("title") and title:
                                existing["title"] = title
                            if not existing.get("submission_date") and submission_date:
                                existing["submission_date"] = submission_date
                            if elapsed_sec and (existing.get("elapsed_seconds") is None or elapsed_sec > existing.get("elapsed_seconds", 0)):
                                existing["elapsed_seconds"] = elapsed_sec

                    # 2. Process Versions
                    seen_versions = set()
                    for v_row in versions_csv_rows:
                        pid = str(v_row.get("arxiv_id", "")).strip()
                        ver = str(safe_int(v_row.get("version")))
                        if pid not in p_csv_lookup or int(ver) < 1:
                            raise ValueError("Invalid version ID or orphan version")

                        status = v_row.get("status", "unknown")
                        if status not in status_priority:
                            raise ValueError(f"Invalid version status: {status}")
                        v_key = (pid, ver)
                        if v_key in seen_versions:
                            raise ValueError("Duplicate version key inside one report")
                        seen_versions.add(v_key)

                        v_entry = {
                            "run_id": run_id,
                            "member": member,
                            "account": account,
                            "arxiv_id": pid,
                            "version": ver,
                            "status": status,
                            "source_bytes_before": safe_float(v_row.get("source_bytes_before")),
                            "source_bytes_after": safe_float(v_row.get("source_bytes_after")),
                            "archive_bytes": safe_float(v_row.get("archive_bytes")),
                            "file_count": safe_int(v_row.get("file_count")),
                            "elapsed_seconds": safe_float(v_row.get("elapsed_seconds")),
                            "attempts": safe_int(v_row.get("attempts", 1)),
                            "used_cache": v_row.get("used_cache", "False"),
                            "error": v_row.get("error", ""),
                        }

                        if v_key not in versions_dict:
                            versions_dict[v_key] = v_entry
                        else:
                            cur_prio = status_priority.get(versions_dict[v_key]["status"], 0)
                            new_prio = status_priority.get(status, 0)
                            if new_prio > cur_prio:
                                versions_dict[v_key] = v_entry

                    # Select a complete reference snapshot per paper; do not union
                    # stale citation sets from unrelated retries.
                    for pid in all_pids:
                        if papers_dict[pid]["_reference_snapshot"] == (run_id, str(zpath)):
                            references_by_paper[pid] = {}
                    for r_row in refs_csv_rows:
                        pid = r_row["arxiv_id"].strip()
                        if pid not in p_csv_lookup:
                            raise ValueError("Orphan reference row")
                        if papers_dict[pid]["_reference_snapshot"] != (run_id, str(zpath)):
                            continue
                        ref_id = canonical_arxiv_id(r_row.get("reference_arxiv_id"))
                        if not ref_id:
                            continue
                        references_by_paper[pid][ref_id] = {
                            "run_id": run_id, "arxiv_id": pid, "reference_arxiv_id": ref_id,
                            **{key: r_row.get(key, "") for key in
                               ("title", "authors", "submission_date", "semantic_scholar_id", "publication_date")},
                        }

                    # 4. Track latest benchmark data across zips for this run
                    if bench_data:
                        run_bench_entry = {
                            "run_id": run_id,
                            "member": member,
                            "account": account,
                            "environment": bench_data.get("environment"),
                            "cpu_only": bench_data.get("cpu_only"),
                            "cache_mode": bench_data.get("cache_mode"),
                            "wall_seconds": bench_data.get("wall_seconds"),
                            "ram_peak_bytes": bench_data.get("ram_peak_bytes"),
                            "ram_mean_bytes": bench_data.get("ram_mean_bytes"),
                            "disk_peak_bytes": bench_data.get("disk_peak_bytes"),
                            "final_disk_bytes": bench_data.get("final_disk_bytes"),
                            "total_papers": bench_data.get("total_papers", run_papers_count),
                            "discovery_elapsed_seconds": run_discovery_seconds,
                        }

            except Exception as e:
                raise ValueError(f"Invalid report archive {zpath}: {e}") from e

        # 5. Extract Resource Samples strictly from the FINAL zip of the run
        # This completely eliminates duplicated sample chains across incremental checkpoints.
        last_zpath = zip_paths[-1]
        try:
            with zipfile.ZipFile(last_zpath, "r") as z_last:
                raw_samples = []
                if "resource_samples.csv" in z_last.namelist():
                    raw_samples = parse_csv_from_zip(z_last, "resource_samples.csv")
                elif "resource_samples.json" in z_last.namelist():
                    json_s = parse_json_from_zip(z_last, "resource_samples.json")
                    if isinstance(json_s, list):
                        raw_samples = json_s
                
                for s in raw_samples:
                    try:
                        resource_samples.append({
                            "run_id": run_id,
                            "member": member,
                            "account": account,
                            "elapsed_seconds": float(s["elapsed_seconds"]),
                            "ram_bytes": int(float(s["ram_bytes"])),
                            "disk_bytes": int(float(s["disk_bytes"])),
                        })
                    except (KeyError, ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"[WARN] Failed to read resource samples from {last_zpath}: {e}")

        if run_bench_entry:
            run_bench_entry["new_unique_papers"] = run_papers_count
            run_bench_entry["discovery_elapsed_seconds"] = run_discovery_seconds
            benchmark_runs.append(run_bench_entry)

        final_zip_sha256 = verified_archives[last_zpath]["sha256"]

        run_metadata.append({
            "run_id": run_id,
            "member": member,
            "account": account,
            "is_checkpoint": is_cp,
            "zip_count": len(zip_paths),
            "papers_extracted": run_papers_count,
            "discovery_elapsed_seconds": run_discovery_seconds,
            "sha256": final_zip_sha256,
            "verified_archives": [dict(path=str(path), **verified_archives[path])
                                  for path in zip_paths],
        })

    if not papers_dict:
        raise ValueError("No paper records found; refusing to publish an empty corpus")
    for pid, paper in papers_dict.items():
        pool = references_by_paper.get(pid, {})
        if len(pool) != paper["kept_references"]:
            raise ValueError(f"Selected arXiv reference pool/count mismatch for {pid}")
        references_dict.update({(pid, key): row for key, row in pool.items()})
    coverage = assignment_coverage(papers_dict, assignment_path)
    print(f"\n[INFO] Extracted {len(papers_dict):,} unique papers across all runs.")
    print(f"[INFO] Extracted {len(versions_dict):,} unique version entries.")
    print(f"[INFO] Extracted {len(references_dict):,} unique reference records.")

    # -------------------------------------------------------------
    # Reconcile paper version metrics and source_status from aggregated versions_dict
    # (Fixes Issue #1 & Cross-Table Consistency: papers_detail vs versions.csv)
    # -------------------------------------------------------------
    paper_versions_map = defaultdict(list)
    for (pid, ver), v_entry in versions_dict.items():
        paper_versions_map[pid].append(v_entry)

    for pid, p in papers_dict.items():
        v_list = paper_versions_map.get(pid, [])
        v_exp = max((int(v["version"]) for v in v_list), default=0)
        v_suc = sum(1 for v in v_list if v["status"] == "success")
        v_notex = sum(1 for v in v_list if v["status"] == "no_tex")
        v_fail = sum(1 for v in v_list if v["status"] == "failed")
        v_pend = sum(1 for v in v_list if v["status"] == "pending")
        missing_versions = max(p["versions_expected"], v_exp) - len(v_list)
        p["versions_missing"] = missing_versions

        p["versions_expected"] = max(p.get("versions_expected", 0), v_exp)
        p["versions_success"] = v_suc
        p["versions_no_tex"] = v_notex
        p["versions_failed"] = v_fail
        p["versions_pending"] = v_pend

        # Strictly enforce: full-source success iff all expected versions contain TeX sources
        if p["versions_expected"] > 0 and v_suc == p["versions_expected"]:
            p["source_status"] = "success"
        else:
            p["source_status"] = "incomplete"

    # Write papers_unique.csv
    papers_unique_path = target_dir / "papers_unique.csv"
    with open(papers_unique_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["member", "account", "run_id", "arxiv_id", "title", "submission_date"])
        writer.writeheader()
        for p in papers_dict.values():
            writer.writerow({
                "member": p["member"],
                "account": p["account"],
                "run_id": p["run_id"],
                "arxiv_id": p["arxiv_id"],
                "title": p["title"],
                "submission_date": p["submission_date"],
            })
    print(f"[SYNC] Wrote {papers_unique_path.name} ({len(papers_dict):,} rows)")

    # Verify invariants
    for p in papers_dict.values():
        t = p.get("total_references")
        k = p.get("kept_references") or 0
        if t is not None and k > t:
            raise ValueError(f"Invariant violation: kept ({k}) > total ({t}) for {p['arxiv_id']}")

    # Write papers_detail.csv
    papers_detail_path = target_dir / "papers_detail.csv"
    with open(papers_detail_path, "w", encoding="utf-8", newline="") as f:
        fields = [
            "arxiv_id", "member", "account", "run_id", "title", "submission_date",
            "metadata_source", "elapsed_seconds", "source_status", "reference_status",
            "versions_expected", "versions_success", "versions_no_tex", "versions_failed",
            "versions_pending", "versions_missing", "total_references", "kept_references", "incomplete_references", "observed_reference_rows"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in papers_dict.values():
            row = {}
            for k in fields:
                val = p.get(k)
                row[k] = "" if val is None else val
            writer.writerow(row)
    print(f"[SYNC] Wrote {papers_detail_path.name} ({len(papers_dict):,} rows)")

    # Write versions.csv
    versions_path = target_dir / "versions.csv"
    with open(versions_path, "w", encoding="utf-8", newline="") as f:
        fields = [
            "run_id", "member", "account", "arxiv_id", "version", "status",
            "source_bytes_before", "source_bytes_after", "archive_bytes",
            "file_count", "elapsed_seconds", "attempts", "used_cache", "error"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for v in versions_dict.values():
            writer.writerow(v)
    print(f"[SYNC] Wrote {versions_path.name} ({len(versions_dict):,} rows)")

    # Write references_agg.csv
    refs_path = target_dir / "references_agg.csv"
    with open(refs_path, "w", encoding="utf-8", newline="") as f:
        fields = [
            "run_id", "arxiv_id", "reference_arxiv_id", "title", "authors",
            "submission_date", "semantic_scholar_id", "publication_date"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in references_dict.values():
            writer.writerow(r)
    print(f"[SYNC] Wrote {refs_path.name} ({len(references_dict):,} rows)")

    # Write resource_samples.csv (subsample if overly large to maintain responsive notebook builds)
    samples_path = target_dir / "resource_samples.csv"
    # Deduplicate samples within runs that have identical elapsed_seconds
    seen_samples = set()
    clean_samples = []
    for s in resource_samples:
        key = (s["run_id"], round(s["elapsed_seconds"], 2))
        if key not in seen_samples:
            seen_samples.add(key)
            clean_samples.append(s)

    clean_samples.sort(key=lambda x: (x["run_id"], x["elapsed_seconds"]))

    sampled_out = clean_samples
    if len(clean_samples) > 30000:
        step = len(clean_samples) // 25000
        sampled_out = clean_samples[::step]
        print(f"[INFO] Subsampled resource traces: {len(clean_samples):,} -> {len(sampled_out):,} points")

    with open(samples_path, "w", encoding="utf-8", newline="") as f:
        fields = ["run_id", "member", "account", "elapsed_seconds", "ram_bytes", "disk_bytes"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in sampled_out:
            writer.writerow(s)
    print(f"[SYNC] Wrote {samples_path.name} ({len(sampled_out):,} rows)")

    # Write run_metadata.json
    run_meta_path = target_dir / "run_metadata.json"
    run_meta_path.write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SYNC] Wrote {run_meta_path.name} ({len(run_metadata)} runs)")

    # -------------------------------------------------------------
    # Compute Aggregated Summary Metrics (Issues #1, #2, #3, #4, #6)
    # -------------------------------------------------------------
    papers_discovered = len(papers_dict)

    # 1. Corpus Completion Metrics (Issue #1: Disambiguate Full-TeX vs Resolved)
    full_tex_papers = sum(
        1 for p in papers_dict.values()
        if p["versions_expected"] > 0 and p["versions_success"] == p["versions_expected"]
    )
    resolved_source_papers = sum(
        1 for p in papers_dict.values()
        if p["versions_expected"] > 0 and (p["versions_success"] + p["versions_no_tex"] >= p["versions_expected"])
    )
    unresolved_source_papers = sum(
        1 for p in papers_dict.values()
        if p["versions_expected"] <= 0 or (p["versions_success"] + p["versions_no_tex"]) < p["versions_expected"]
    )
    # Backwards compatibility: full_source_papers maps to all resolved papers
    full_source_papers = resolved_source_papers

    v_success = sum(1 for v in versions_dict.values() if v["status"] == "success")
    v_notex = sum(1 for v in versions_dict.values() if v["status"] == "no_tex")
    v_failed = sum(1 for v in versions_dict.values() if v["status"] == "failed")
    v_pending = sum(1 for v in versions_dict.values() if v["status"] == "pending")
    versions_expected = sum(p["versions_expected"] for p in papers_dict.values())

    # 2. Reference Ingestion & Pool Metrics (Issue #2 & Issue #3)
    ref_jobs_success = sum(1 for p in papers_dict.values() if p.get("reference_status") == "success")
    ref_jobs_partial = sum(1 for p in papers_dict.values() if p.get("reference_status") == "partial")
    ref_jobs_failed = sum(1 for p in papers_dict.values() if p.get("reference_status") == "failed")
    ref_jobs_not_found = sum(1 for p in papers_dict.values() if p.get("reference_status") == "not_found")
    ref_jobs_pending = sum(1 for p in papers_dict.values() if p.get("reference_status") in [None, "", "pending"])

    papers_with_arxiv_pool = len(set(r["arxiv_id"] for r in references_dict.values()))
    papers_with_non_arxiv_only = sum(
        1 for p in papers_dict.values()
        if p.get("reference_status") == "success" and (p.get("kept_references") or 0) == 0 and (p.get("total_references") or 0) > 0
    )

    total_extracted_refs_confirmed = sum(
        p["total_references"] for p in papers_dict.values() if p.get("total_references") is not None
    )
    observed_counts = [p["observed_reference_rows"] for p in papers_dict.values()]
    total_extracted_refs_observed = (sum(observed_counts) if all(v is not None for v in observed_counts) else None)
    observed_reference_lower_bound = sum(
        p["observed_reference_rows"] if p["observed_reference_rows"] is not None else p["kept_references"]
        for p in papers_dict.values()
    )

    # Backward compatibility: total_extracted_refs is the confirmed reference count
    total_extracted_refs = total_extracted_refs_confirmed

    total_kept_refs = sum(p.get("kept_references") or 0 for p in papers_dict.values())
    confirmed_kept_refs = sum(
        p.get("kept_references") or 0 for p in papers_dict.values() if p.get("total_references") is not None
    )
    total_non_arxiv_refs = max(0, total_extracted_refs_confirmed - confirmed_kept_refs)

    arxiv_ref_rows = len(references_dict)
    crawled_ref_rows = total_extracted_refs
    non_arxiv_ref_rows = total_non_arxiv_refs

    completed_papers_count = sum(1 for p in papers_dict.values() if p.get("total_references") is not None)
    mean_refs_confirmed = total_extracted_refs_confirmed / completed_papers_count if completed_papers_count else 0.0
    mean_refs_observed = total_extracted_refs_observed / len(papers_dict) if total_extracted_refs_observed is not None else None
    mean_arxiv_refs = total_kept_refs / len(papers_dict) if papers_dict else 0.0

    # Audit reference completeness rate: (kept - incomplete) / kept
    comp_list = []
    for p in papers_dict.values():
        k = p.get("kept_references") or 0
        if k > 0 and p.get("incomplete_references") is not None:
            inc = p["incomplete_references"]
            comp_list.append(max(0.0, (k - inc) / k))
    avg_completeness = sum(comp_list) / len(comp_list) if comp_list else None

    # 3. Paired Source Size Reductions (Issue #4: Matched Populations)
    # Subset A: Paired TeX-success versions (both before and after contain positive byte counts)
    paired_tex_before = [
        v["source_bytes_before"] for v in versions_dict.values()
        if v["status"] == "success" and v.get("source_bytes_before") and v.get("source_bytes_after")
    ]
    paired_tex_after = [
        v["source_bytes_after"] for v in versions_dict.values()
        if v["status"] == "success" and v.get("source_bytes_before") and v.get("source_bytes_after")
    ]
    avg_tex_v_before = sum(paired_tex_before) / len(paired_tex_before) if paired_tex_before else 0.0
    avg_tex_v_after = sum(paired_tex_after) / len(paired_tex_after) if paired_tex_after else 0.0
    tex_v_reduction = 1.0 - (sum(paired_tex_after) / sum(paired_tex_before)) if paired_tex_before else 0.0

    # Subset B: Paired All-resolved versions (including no_tex where post-extraction byte count = 0.0)
    paired_res_before = [
        v["source_bytes_before"] for v in versions_dict.values()
        if v["status"] in ("success", "no_tex") and v.get("source_bytes_before") is not None
    ]
    paired_res_after = [
        (v["source_bytes_after"] if v["status"] == "success" and v.get("source_bytes_after") else 0.0)
        for v in versions_dict.values()
        if v["status"] in ("success", "no_tex") and v.get("source_bytes_before") is not None
    ]
    avg_res_v_before = sum(paired_res_before) / len(paired_res_before) if paired_res_before else 0.0
    avg_res_v_after = sum(paired_res_after) / len(paired_res_after) if paired_res_after else 0.0
    res_v_reduction = 1.0 - (sum(paired_res_after) / sum(paired_res_before)) if paired_res_before else 0.0

    # Subset C: Paired Paper-level aggregations
    paper_bytes_before = defaultdict(float)
    paper_bytes_after = defaultdict(float)
    for v in versions_dict.values():
        pid = v["arxiv_id"]
        if v.get("source_bytes_before"):
            paper_bytes_before[pid] += v["source_bytes_before"]
        if v.get("status") == "success" and v.get("source_bytes_after"):
            paper_bytes_after[pid] += v["source_bytes_after"]

    # Full-TeX papers (strictly paired across all versions)
    tex_p_pids = [
        pid for pid, p in papers_dict.items()
        if p["versions_expected"] > 0 and p["versions_success"] == p["versions_expected"]
        and paper_bytes_before.get(pid, 0) > 0
    ]
    tex_p_before = [paper_bytes_before[pid] for pid in tex_p_pids]
    tex_p_after = [paper_bytes_after[pid] for pid in tex_p_pids]
    avg_tex_p_before = sum(tex_p_before) / len(tex_p_before) if tex_p_before else 0.0
    avg_tex_p_after = sum(tex_p_after) / len(tex_p_after) if tex_p_after else 0.0

    # All resolved papers (strictly paired across all versions)
    res_p_pids = [
        pid for pid, p in papers_dict.items()
        if p["versions_expected"] > 0 and (p["versions_success"] + p["versions_no_tex"] >= p["versions_expected"])
        and paper_bytes_before.get(pid, 0) > 0
    ]
    res_p_before = [paper_bytes_before[pid] for pid in res_p_pids]
    res_p_after = [paper_bytes_after[pid] for pid in res_p_pids]
    avg_res_p_before = sum(res_p_before) / len(res_p_before) if res_p_before else 0.0
    avg_res_p_after = sum(res_p_after) / len(res_p_after) if res_p_after else 0.0

    # Processing time per paper
    p_times = [p["elapsed_seconds"] for p in papers_dict.values() if p.get("elapsed_seconds") is not None and p["elapsed_seconds"] > 0]
    avg_paper_seconds = sum(p_times) / len(p_times) if p_times else 0.0

    # Member breakdown
    member_breakdown = defaultdict(lambda: {"papers": 0, "accounts": set(), "runs": set()})
    for p in papers_dict.values():
        m = p["member"]
        member_breakdown[m]["papers"] += 1
        member_breakdown[m]["accounts"].add(p["account"])
        member_breakdown[m]["runs"].add(p["run_id"])

    bench_runs_by_member = Counter(r.get("member") for r in benchmark_runs)

    member_summary = {
        m: {
            "papers": data["papers"],
            "accounts_count": len(data["accounts"]),
            "selected_runs_count": len(data["runs"]),
            "runs_count": len(data["runs"]),  # backward compatibility
            "benchmark_runs_count": bench_runs_by_member.get(m, 0),
        }
        for m, data in member_breakdown.items()
    }

    paper_field_audit = {}
    for field in ("title", "authors", "submission_date", "revised_dates", "venue"):
        audited = [p["_metadata"][field] for p in papers_dict.values() if field in p["_metadata"]]
        present = sum(bool(v) or (field == "revised_dates" and isinstance(v, list)) for v in audited)
        paper_field_audit[field] = {"audited": len(audited), "present": present,
                                    "missing": len(audited) - present, "unknown": len(papers_dict) - len(audited)}
    reference_field_audit = {}
    for field in ("title", "authors", "submission_date", "semantic_scholar_id"):
        present = sum(bool(str(r.get(field) or "").strip()) and str(r.get(field)).strip() != "[]"
                      for r in references_dict.values())
        reference_field_audit[field] = {"audited": len(references_dict), "present": present,
                                       "missing": len(references_dict) - present}

    summary_data = {
        "papers_discovered": papers_discovered,
        **coverage,
        "selected_runs_total": len(set(p["run_id"] for p in papers_dict.values())),
        "benchmark_runs_total": len(benchmark_runs),
        "full_tex_papers": full_tex_papers,
        "full_tex_paper_rate": full_tex_papers / papers_discovered if papers_discovered else 0.0,
        "resolved_source_papers": resolved_source_papers,
        "resolved_source_rate": resolved_source_papers / papers_discovered if papers_discovered else 0.0,
        "unresolved_source_papers": unresolved_source_papers,
        "full_source_papers": resolved_source_papers,
        "paper_success_rate": resolved_source_papers / papers_discovered if papers_discovered else 0.0,

        "versions_expected": versions_expected,
        "versions_success": v_success,
        "versions_no_tex": v_notex,
        "versions_failed": v_failed,
        "versions_pending": v_pending,
        "versions_missing": sum(p["versions_missing"] for p in papers_dict.values()),
        "source_coverage_rate": (v_success + v_notex) / versions_expected if versions_expected else 0.0,

        "reference_jobs_success": ref_jobs_success,
        "reference_jobs_partial": ref_jobs_partial,
        "reference_jobs_failed": ref_jobs_failed,
        "reference_jobs_not_found": ref_jobs_not_found,
        "reference_jobs_pending": ref_jobs_pending,
        "reference_api_success_rate": ref_jobs_success / papers_discovered if papers_discovered else 0.0,
        "papers_with_arxiv_pool": papers_with_arxiv_pool,
        "papers_with_arxiv_pool_rate": papers_with_arxiv_pool / papers_discovered if papers_discovered else 0.0,
        "papers_with_non_arxiv_only": papers_with_non_arxiv_only,
        "reference_success_rate": ref_jobs_success / papers_discovered if papers_discovered else 0.0,

        "total_extracted_references": total_extracted_refs,
        "total_extracted_references_confirmed": total_extracted_refs_confirmed,
        "total_extracted_references_observed": total_extracted_refs_observed,
        "observed_reference_lower_bound": observed_reference_lower_bound,
        "unknown_reference_total_papers": sum(v is None for v in observed_counts),
        "confirmed_reference_papers_count": completed_papers_count,
        "crawled_reference_rows": total_extracted_refs,
        "arxiv_reference_rows": arxiv_ref_rows,
        "non_arxiv_reference_rows": non_arxiv_ref_rows,
        "average_reference_count": mean_refs_confirmed,
        "average_reference_count_confirmed": mean_refs_confirmed,
        "average_reference_count_observed": mean_refs_observed,
        "average_arxiv_reference_count": mean_arxiv_refs,
        "reference_count_denominator": completed_papers_count,
        "all_papers_count": papers_discovered,

        "average_reference_completeness_rate": avg_completeness,
        "reference_completeness_denominator": len(comp_list),

        "metadata_field_audit": {
            "paper_fields": paper_field_audit,
            "reference_fields": reference_field_audit,
            "scope": "Field presence in selected manifest/pool; no independent upstream correctness audit",
            "total_papers_audited": len(papers_dict),
            "title_present": sum(1 for p in papers_dict.values() if p.get("title")),
            "submission_date_present": sum(1 for p in papers_dict.values() if p.get("submission_date")),
            "metadata_source_present": sum(1 for p in papers_dict.values() if p.get("metadata_source")),
            "missing_titles": sum(1 for p in papers_dict.values() if not p.get("title")),
            "missing_submission_dates": sum(1 for p in papers_dict.values() if not p.get("submission_date")),
        },

        "average_paper_processing_seconds": avg_paper_seconds,
        "paper_time_denominator": len(p_times),

        "paired_tex_versions_count": len(paired_tex_before),
        "average_tex_source_bytes_before": avg_tex_v_before,
        "average_tex_source_bytes_after": avg_tex_v_after,
        "tex_size_reduction_ratio": tex_v_reduction,

        "source_size_denominator": len(paired_res_before),
        "average_source_bytes_before": avg_res_v_before,
        "average_source_bytes_after": avg_res_v_after,
        "size_reduction_ratio": res_v_reduction,

        "paired_tex_paper_denominator": len(tex_p_before),
        "average_tex_paper_source_bytes_before": avg_tex_p_before,
        "average_tex_paper_source_bytes_after": avg_tex_p_after,

        "paper_size_denominator": len(res_p_before),
        "average_paper_source_bytes_before": avg_res_p_before,
        "average_paper_source_bytes_after": avg_res_p_after,

        "member_breakdown": member_summary,
    }

    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"[SYNC] Wrote {summary_path.name}")

    # -------------------------------------------------------------
    # Compute Aggregated Benchmark (Issues #5, #6, #8)
    # -------------------------------------------------------------
    wall_times = [r["wall_seconds"] for r in benchmark_runs if r.get("wall_seconds") is not None]
    peak_rams = [r["ram_peak_bytes"] for r in benchmark_runs if r.get("ram_peak_bytes") is not None]
    mean_rams = [r["ram_mean_bytes"] for r in benchmark_runs if r.get("ram_mean_bytes") is not None]
    peak_disks = [r["disk_peak_bytes"] for r in benchmark_runs if r.get("disk_peak_bytes") is not None]
    final_disks = [r["final_disk_bytes"] for r in benchmark_runs if r.get("final_disk_bytes") is not None]

    wall_times_sorted = sorted(wall_times)
    median_wall = statistics.median(wall_times_sorted) if wall_times_sorted else None
    total_wall = sum(wall_times) if len(wall_times) == len(benchmark_runs) else None

    merged_tex_bib_bytes = sum(v["source_bytes_after"] for v in versions_dict.values() if v.get("source_bytes_after"))
    sum_final_disks = sum(final_disks) if len(final_disks) == len(benchmark_runs) else None

    # Final merged filesystem size requires an actual merged tree and a defined
    # selection policy. ZIP central-directory sizes are not that measurement.
    corpus_archive_count = 0
    for item in run_configs:
        corpus_evidence = []
        for zpath in item["zip_paths"]:
            corpus_path = zpath.with_name("corpus.zip")
            if corpus_path.is_file():
                evidence = verify_report_archive(corpus_path, item["run_id"], kind="corpus")
                with zipfile.ZipFile(corpus_path) as archive:
                    bad_member = archive.testzip()
                    if bad_member is not None:
                        raise ValueError(f"Invalid corpus member: {bad_member}")
                corpus_evidence.append(dict(path=str(corpus_path), **evidence))
                corpus_archive_count += 1
        for run in run_metadata:
            if run["run_id"] == item["run_id"] and run["member"] == item["member"] and run["account"] == item["account"]:
                run["verified_corpus_archives"] = corpus_evidence
    run_meta_path.write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    merged_corpus_uncompressed_bytes = None
    merged_corpus_file_count = None

    cpu_flags = [r.get("cpu_only") for r in benchmark_runs]
    cpu_only = (False if any(value is False for value in cpu_flags) else
                True if cpu_flags and all(value is True for value in cpu_flags) else None)
    cache_modes = sorted({r["cache_mode"] for r in benchmark_runs if r.get("cache_mode")})
    missing_cache_modes = any(not r.get("cache_mode") for r in benchmark_runs)
    cache_description = ("unknown (run cache metadata missing)" if missing_cache_modes or not cache_modes
                         else cache_modes[0] if len(cache_modes) == 1 else "mixed: " + ", ".join(cache_modes))
    cached_versions = sum(str(v.get("used_cache", "")).lower() == "true" for v in versions_dict.values())

    benchmark_data = {
        # Top-level backwards compatibility fields:
        "environment": "; ".join(sorted({r["environment"] for r in benchmark_runs if r.get("environment")})) or None,
        "cpu_only": cpu_only,
        "cache_mode": cache_description,
        "cached_source_versions": cached_versions,
        "sampling_interval_seconds": 0.25,
        "wall_seconds": total_wall,
        "median_wall_seconds": median_wall,
        "ram_peak_bytes": max(peak_rams) if peak_rams else None,
        "ram_mean_bytes": sum(mean_rams) / len(mean_rams) if mean_rams else None,
        "disk_peak_bytes": max(peak_disks) if peak_disks else None,
        "final_disk_bytes": sum_final_disks,
        "sum_run_final_disk_bytes": sum_final_disks,
        "merged_corpus_tex_bib_bytes": merged_tex_bib_bytes,
        "merged_corpus_uncompressed_bytes": merged_corpus_uncompressed_bytes,
        "merged_corpus_file_count": merged_corpus_file_count,
        "merged_corpus_measurement_status": "not measured: no selected merged filesystem tree",
        "verified_corpus_archive_count": corpus_archive_count,
        "disk_capacity_bytes": None,
        "tracked_paths": None,
        "measurement_run_counts": {key: sum(r.get(key) is not None for r in benchmark_runs)
                                   for key in ("wall_seconds", "ram_peak_bytes", "ram_mean_bytes", "disk_peak_bytes", "final_disk_bytes")},
        # Multi-run aggregation details:
        "multi_run_summary": {
            "total_runs": len(benchmark_runs),
            "median_wall_seconds": median_wall,
            "total_wall_seconds": total_wall,
            "max_ram_peak_bytes": max(peak_rams) if peak_rams else None,
            "mean_ram_bytes_across_runs": sum(mean_rams) / len(mean_rams) if mean_rams else None,
            "total_discovery_elapsed_seconds": sum(r.get("discovery_elapsed_seconds", 0) for r in benchmark_runs),
            "sum_run_final_disk_bytes": sum_final_disks,
            "merged_corpus_tex_bib_bytes": merged_tex_bib_bytes,
            "merged_corpus_uncompressed_bytes": merged_corpus_uncompressed_bytes,
            "merged_corpus_file_count": merged_corpus_file_count,
        },
        "runs": benchmark_runs,
    }

    benchmark_path = target_dir / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark_data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"[SYNC] Wrote {benchmark_path.name} ({len(benchmark_runs)} runs documented)")

    return {
        "summary": summary_data,
        "benchmark": benchmark_data,
        "papers_count": len(papers_dict),
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate 20,000-paper crawl measurements into Jupyter Book.")
    parser.add_argument("--source", type=str, default=None, help="Path to input directory containing member data.")
    parser.add_argument("--target", type=str, default=None, help="Destination directory (default: book/data).")
    parser.add_argument("--build", action="store_true", help="Rebuild Jupyter Book immediately.")
    parser.add_argument("--assignments", type=Path, help="Versioned assignment manifest (default: config/assignments.json)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target_dir = Path(args.target) if args.target else repo_root / "book/data"

    if args.source:
        source_dir = Path(args.source).resolve()
    else:
        source_dir = find_default_source()

    if not source_dir.is_dir():
        print(f"[ERROR] Source directory does not exist: {source_dir}")
        sys.exit(1)

    print("============================================================")
    print("      arXiv Milestone 1 — Data Aggregation Pipeline        ")
    print("============================================================")
    print(f"Source Directory: {source_dir}")
    print(f"Target Directory: {target_dir}")

    results = aggregate_corpus(source_dir, target_dir, args.assignments)

    print("\n---------------- Aggregated Corpus Audit ----------------")
    s = results["summary"]
    b = results["benchmark"]
    print(f"• Total Papers Discovered:       {s['papers_discovered']:,} (Target: 20,000)")
    print(f"• Full-TeX Source Papers:        {s['full_tex_papers']:,} ({s['full_tex_paper_rate']*100:.2f}%)")
    print(f"• Resolved Outcome Papers:       {s['resolved_source_papers']:,} ({s['resolved_source_rate']*100:.2f}%)")
    print(f"• Unresolved / Failed Papers:    {s['unresolved_source_papers']:,}")
    print(f"• Total Versions Expected:       {s['versions_expected']:,}")
    print(f"• Versions Success (TeX):        {s['versions_success']:,} ({s['source_coverage_rate']*100:.2f}%)")
    print(f"• Versions Without TeX:          {s['versions_no_tex']:,}")
    print(f"• Versions Failed:               {s['versions_failed']:,}")
    print(f"• Total Extracted References:    {s['total_extracted_references']:,}")
    print(f"• Reference Jobs Succeeded:      {s['reference_jobs_success']:,} ({s['reference_api_success_rate']*100:.2f}%)")
    print(f"• Papers with arXiv Ref Pool:    {s['papers_with_arxiv_pool']:,} ({s['papers_with_arxiv_pool_rate']*100:.2f}%)")
    print(f"• Paired TeX Size Reduction:     {s['tex_size_reduction_ratio']*100:.2f}% (N = {s['paired_tex_versions_count']:,} versions)")
    print(f"• All-Resolved Size Reduction:   {s['size_reduction_ratio']*100:.2f}% (N = {s['source_size_denominator']:,} versions)")
    print(f"• Avg Paired Source Before/After:{s['average_source_bytes_before']/(1024):,.1f} KiB -> {s['average_source_bytes_after']/(1024):,.1f} KiB")
    print(f"• Merged Corpus TeX/Bib Size:    {b['merged_corpus_tex_bib_bytes']/(1024**3):.2f} GiB")
    disk = b['sum_run_final_disk_bytes']
    print("• Sum of Run Final Disks:        " + (f"{disk/(1024**3):.2f} GiB" if disk is not None else "Not measured for all runs"))
    print(f"• Member Breakdown:")
    for m, mdata in s.get("member_breakdown", {}).items():
        print(f"    - {m:<10}: {mdata['papers']:,} papers ({mdata['runs_count']} runs across {mdata['accounts_count']} accounts)")
    print("---------------------------------------------------------")
    print(f"[SUCCESS] All target datasets in {target_dir} generated successfully!\n")

    if args.build:
        print("=== Building Jupyter Book ===")
        venv_jb = Path(sys.executable).with_name("jupyter-book.exe" if os.name == "nt" else "jupyter-book")
        jb_cmd = str(venv_jb) if venv_jb.is_file() else "jupyter-book"
        res = subprocess.run([jb_cmd, "build", "--all", str(repo_root / "book")], check=False)
        if res.returncode == 0:
            print("[SUCCESS] Jupyter Book rebuild completed cleanly.")
        else:
            print(f"[FAIL] Jupyter Book build exited with code {res.returncode}")
            sys.exit(res.returncode)


if __name__ == "__main__":
    main()
