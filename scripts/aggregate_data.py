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
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
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


def verify_report_archive(path: Path, run_id: str) -> Dict[str, Any]:
    """Match an input report ZIP to its adjacent crawler completion receipt."""
    receipt_path = path.with_name("backup_receipt.json")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        entry = receipt["archives"]["report"]
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
            "sha256": actual_hash, "verified": True}


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


def parse_csv_from_zip(z: zipfile.ZipFile, filename: str) -> List[Dict[str, str]]:
    """Extract and parse CSV from zip archive into list of dicts, ensuring string types."""
    if filename not in z.namelist():
        return []
    try:
        content = z.read(filename).decode("utf-8", errors="replace")
        reader = csv.DictReader(content.splitlines())
        return list(reader)
    except Exception as e:
        print(f"[WARN] Failed to parse {filename} in zip: {e}")
        return []


def parse_json_from_zip(z: zipfile.ZipFile, filename: str) -> Optional[Any]:
    """Extract and parse JSON from zip archive."""
    if filename not in z.namelist():
        return None
    try:
        return json.loads(z.read(filename).decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"[WARN] Failed to parse {filename} in zip: {e}")
        return None


def aggregate_corpus(source_dir: Path, target_dir: Path) -> Dict[str, Any]:
    """Core aggregation pipeline processing all runs into book/data/ files."""
    print(f"[INFO] Scanning runs from {source_dir}...")
    run_configs = collect_runs(source_dir)
    print(f"[INFO] Discovered {len(run_configs)} total run entries.")

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
                    manifest = parse_json_from_zip(z, "manifest.json")
                    papers_csv_rows = parse_csv_from_zip(z, "papers.csv")
                    versions_csv_rows = parse_csv_from_zip(z, "versions.csv")
                    refs_csv_rows = parse_csv_from_zip(z, "references.csv")
                    if not refs_csv_rows:
                        refs_csv_rows = parse_csv_from_zip(z, "references_all.csv")
                    bench_data = parse_json_from_zip(z, "benchmark.json")

                    # Handle discovery time
                    if manifest and "discovery" in manifest:
                        disc = manifest["discovery"]
                        disc_sec = disc.get("elapsed_seconds")
                        if disc_sec and isinstance(disc_sec, (int, float)):
                            run_discovery_seconds = max(run_discovery_seconds, float(disc_sec))

                    # 1. Process Papers
                    # Build lookup from papers.csv rows
                    p_csv_lookup = {r["arxiv_id"]: r for r in papers_csv_rows if "arxiv_id" in r}

                    manifest_papers = manifest.get("papers", {}) if manifest else {}

                    # Union of all arxiv_ids in this zip
                    all_pids = set(manifest_papers.keys()) | set(p_csv_lookup.keys())
                    for pid in all_pids:
                        pid_str = str(pid).strip()
                        if not pid_str:
                            continue

                        p_info = manifest_papers.get(pid_str, {})
                        rec = p_info.get("record", {}) if isinstance(p_info, dict) else {}
                        meta = rec.get("metadata", {}) if isinstance(rec, dict) else {}
                        csv_info = p_csv_lookup.get(pid_str, {})

                        title = meta.get("title") or csv_info.get("title") or ""
                        submission_date = meta.get("submission_date") or csv_info.get("submission_date") or ""

                        # Convert elapsed_seconds safely
                        elapsed_sec = None
                        if "elapsed_seconds" in csv_info and csv_info["elapsed_seconds"]:
                            try:
                                elapsed_sec = float(csv_info["elapsed_seconds"])
                            except ValueError:
                                pass
                        elif "elapsed_seconds" in p_info and p_info["elapsed_seconds"] is not None:
                            try:
                                elapsed_sec = float(p_info["elapsed_seconds"])
                            except ValueError:
                                pass

                        def safe_int(val, default=0):
                            if val is None or val == "":
                                return default
                            try:
                                return int(val)
                            except (ValueError, TypeError):
                                return default

                        v_exp = safe_int(csv_info.get("versions_expected"))
                        v_suc = safe_int(csv_info.get("versions_success"))
                        v_notex = safe_int(csv_info.get("versions_no_tex"))
                        v_fail = safe_int(csv_info.get("versions_failed"))
                        v_pend = safe_int(csv_info.get("versions_pending"))
                        t_refs = safe_int(csv_info.get("total_references"))
                        k_refs = safe_int(csv_info.get("kept_references"))
                        inc_refs = safe_int(csv_info.get("incomplete_references"))

                        source_status = csv_info.get("source_status") or "unknown"
                        ref_status = csv_info.get("reference_status") or "unknown"

                        paper_record = {
                            "arxiv_id": pid_str,
                            "member": member,
                            "account": account,
                            "run_id": run_id,
                            "title": title,
                            "submission_date": submission_date,
                            "metadata_source": csv_info.get("metadata_source", "oai-pmh/arXivRaw"),
                            "elapsed_seconds": elapsed_sec,
                            "source_status": source_status,
                            "reference_status": ref_status,
                            "versions_expected": v_exp,
                            "versions_success": v_suc,
                            "versions_no_tex": v_notex,
                            "versions_failed": v_fail,
                            "versions_pending": v_pend,
                            "total_references": t_refs,
                            "kept_references": k_refs,
                            "incomplete_references": inc_refs,
                        }

                        # Deduplicate: if exists, keep the one with higher success/more complete info
                        if pid_str not in papers_dict:
                            papers_dict[pid_str] = paper_record
                            run_papers_count += 1
                        else:
                            existing = papers_dict[pid_str]
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

                            if not existing.get("title") and title:
                                existing["title"] = title
                            if not existing.get("submission_date") and submission_date:
                                existing["submission_date"] = submission_date
                            if elapsed_sec and (existing.get("elapsed_seconds") is None or elapsed_sec > existing.get("elapsed_seconds", 0)):
                                existing["elapsed_seconds"] = elapsed_sec

                    # 2. Process Versions
                    for v_row in versions_csv_rows:
                        pid = str(v_row.get("arxiv_id", "")).strip()
                        ver = str(v_row.get("version", "")).strip()
                        if not pid or not ver:
                            continue

                        status = v_row.get("status", "unknown")
                        v_key = (pid, ver)

                        def safe_float(v):
                            try:
                                return float(v) if v is not None and v != "" else None
                            except ValueError:
                                return None

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

                    # 3. Process References
                    for r_row in refs_csv_rows:
                        pid = str(r_row.get("arxiv_id", "")).strip()
                        ref_id = str(r_row.get("reference_arxiv_id", "")).strip()
                        ref_title = r_row.get("title", "").strip()
                        if not pid or (not ref_id and not ref_title):
                            continue

                        # Composite key for reference
                        ref_key = (pid, ref_id if ref_id else ref_title[:50])
                        if ref_key not in references_dict:
                            references_dict[ref_key] = {
                                "run_id": run_id,
                                "arxiv_id": pid,
                                "reference_arxiv_id": ref_id,
                                "title": ref_title,
                                "authors": r_row.get("authors", ""),
                                "submission_date": r_row.get("submission_date", ""),
                                "semantic_scholar_id": r_row.get("semantic_scholar_id", ""),
                                "publication_date": r_row.get("publication_date", ""),
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
                print(f"[ERROR] Failed to read {zpath}: {e}")

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
            run_bench_entry["total_papers"] = run_papers_count
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
        v_exp = len(v_list)
        v_suc = sum(1 for v in v_list if v["status"] == "success")
        v_notex = sum(1 for v in v_list if v["status"] == "no_tex")
        v_fail = sum(1 for v in v_list if v["status"] == "failed")
        v_pend = sum(1 for v in v_list if v["status"] == "pending")

        p["versions_expected"] = max(p.get("versions_expected", 0), v_exp)
        p["versions_success"] = v_suc
        p["versions_no_tex"] = v_notex
        p["versions_failed"] = v_fail
        p["versions_pending"] = v_pend

        # Strictly enforce: full-source success iff all expected versions contain TeX sources
        if v_exp > 0 and v_suc == v_exp:
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

    # Write papers_detail.csv
    papers_detail_path = target_dir / "papers_detail.csv"
    with open(papers_detail_path, "w", encoding="utf-8", newline="") as f:
        fields = [
            "arxiv_id", "member", "account", "run_id", "title", "submission_date",
            "metadata_source", "elapsed_seconds", "source_status", "reference_status",
            "versions_expected", "versions_success", "versions_no_tex", "versions_failed",
            "versions_pending", "total_references", "kept_references"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in papers_dict.values():
            writer.writerow({k: p.get(k) for k in fields})
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
        if p["versions_failed"] > 0 or p["versions_pending"] > 0
    )
    # Backwards compatibility: full_source_papers maps to all resolved papers
    full_source_papers = resolved_source_papers

    v_success = sum(1 for v in versions_dict.values() if v["status"] == "success")
    v_notex = sum(1 for v in versions_dict.values() if v["status"] == "no_tex")
    v_failed = sum(1 for v in versions_dict.values() if v["status"] == "failed")
    v_pending = sum(1 for v in versions_dict.values() if v["status"] == "pending")
    versions_expected = len(versions_dict)

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

    total_extracted_refs = sum(p.get("total_references") or 0 for p in papers_dict.values())
    total_kept_refs = sum(p.get("kept_references") or 0 for p in papers_dict.values())
    total_non_arxiv_refs = max(0, total_extracted_refs - total_kept_refs)

    arxiv_ref_rows = len(references_dict)
    crawled_ref_rows = total_extracted_refs
    non_arxiv_ref_rows = total_non_arxiv_refs

    # Audit reference completeness rate: (kept - incomplete) / kept
    comp_list = []
    for p in papers_dict.values():
        k = p.get("kept_references") or 0
        if k > 0:
            inc = p.get("incomplete_references") or 0
            comp_list.append(max(0.0, (k - inc) / k))
    avg_completeness = sum(comp_list) / len(comp_list) if comp_list else 1.0

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

    member_summary = {
        m: {
            "papers": data["papers"],
            "accounts_count": len(data["accounts"]),
            "runs_count": len(data["runs"]),
        }
        for m, data in member_breakdown.items()
    }

    summary_data = {
        "papers_discovered": papers_discovered,
        "id_discovery_coverage": 1.0,
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
        "crawled_reference_rows": total_extracted_refs,
        "arxiv_reference_rows": arxiv_ref_rows,
        "non_arxiv_reference_rows": non_arxiv_ref_rows,
        "average_reference_count": total_extracted_refs / papers_discovered if papers_discovered else 0.0,
        "average_arxiv_reference_count": arxiv_ref_rows / papers_discovered if papers_discovered else 0.0,
        "reference_count_denominator": papers_discovered,

        "average_reference_completeness_rate": avg_completeness,
        "reference_completeness_denominator": len(comp_list),

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
    summary_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SYNC] Wrote {summary_path.name}")

    # -------------------------------------------------------------
    # Compute Aggregated Benchmark (Issues #5, #6, #8)
    # -------------------------------------------------------------
    wall_times = [r["wall_seconds"] for r in benchmark_runs if r.get("wall_seconds")]
    peak_rams = [r["ram_peak_bytes"] for r in benchmark_runs if r.get("ram_peak_bytes")]
    mean_rams = [r["ram_mean_bytes"] for r in benchmark_runs if r.get("ram_mean_bytes")]
    peak_disks = [r["disk_peak_bytes"] for r in benchmark_runs if r.get("disk_peak_bytes")]
    final_disks = [r["final_disk_bytes"] for r in benchmark_runs if r.get("final_disk_bytes")]

    wall_times_sorted = sorted(wall_times)
    median_wall = wall_times_sorted[len(wall_times_sorted) // 2] if wall_times_sorted else 0.0
    total_wall = sum(wall_times)

    merged_tex_bib_bytes = sum(v["source_bytes_after"] for v in versions_dict.values() if v.get("source_bytes_after"))
    sum_final_disks = sum(final_disks) if final_disks else 0
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
        "ram_peak_bytes": max(peak_rams) if peak_rams else 0,
        "ram_mean_bytes": sum(mean_rams) / len(mean_rams) if mean_rams else 0,
        "disk_peak_bytes": max(peak_disks) if peak_disks else 0,
        "final_disk_bytes": sum_final_disks,
        "sum_run_final_disk_bytes": sum_final_disks,
        "merged_corpus_tex_bib_bytes": merged_tex_bib_bytes,
        # Multi-run aggregation details:
        "multi_run_summary": {
            "total_runs": len(benchmark_runs),
            "median_wall_seconds": median_wall,
            "total_wall_seconds": total_wall,
            "max_ram_peak_bytes": max(peak_rams) if peak_rams else 0,
            "mean_ram_bytes_across_runs": sum(mean_rams) / len(mean_rams) if mean_rams else 0,
            "total_discovery_elapsed_seconds": sum(r.get("discovery_elapsed_seconds", 0) for r in benchmark_runs),
            "sum_run_final_disk_bytes": sum_final_disks,
            "merged_corpus_tex_bib_bytes": merged_tex_bib_bytes,
        },
        "runs": benchmark_runs,
    }

    benchmark_path = target_dir / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark_data, indent=2, ensure_ascii=False), encoding="utf-8")
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

    results = aggregate_corpus(source_dir, target_dir)

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
    print(f"• Sum of Run Final Disks:        {b['sum_run_final_disk_bytes']/(1024**3):.2f} GiB")
    print(f"• Member Breakdown:")
    for m, mdata in s.get("member_breakdown", {}).items():
        print(f"    - {m:<10}: {mdata['papers']:,} papers ({mdata['runs_count']} runs across {mdata['accounts_count']} accounts)")
    print("---------------------------------------------------------")
    print(f"[SUCCESS] All target datasets in {target_dir} generated successfully!\n")

    if args.build:
        print("=== Building Jupyter Book ===")
        venv_jb = repo_root.parent / ".venv/Scripts/jupyter-book.exe"
        jb_cmd = str(venv_jb) if venv_jb.is_file() else "jupyter-book"
        res = subprocess.run([jb_cmd, "build", "--all", str(repo_root / "book")], check=False)
        if res.returncode == 0:
            print("[SUCCESS] Jupyter Book rebuild completed cleanly.")
        else:
            print(f"[FAIL] Jupyter Book build exited with code {res.returncode}")
            sys.exit(res.returncode)


if __name__ == "__main__":
    main()
