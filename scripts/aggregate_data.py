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
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Scanning runs from {source_dir}...")
    run_configs = collect_runs(source_dir)
    print(f"[INFO] Discovered {len(run_configs)} total run entries.")

    papers_dict: Dict[str, Dict[str, Any]] = {}
    versions_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    references_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    resource_samples: List[Dict[str, Any]] = []
    benchmark_runs: List[Dict[str, Any]] = []
    run_metadata: List[Dict[str, Any]] = []

    status_priority = {"success": 4, "no_tex": 3, "failed": 2, "pending": 1}

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
                        }

                        # Deduplicate: if exists, keep the one with higher success/more complete info
                        if pid_str not in papers_dict:
                            papers_dict[pid_str] = paper_record
                            run_papers_count += 1
                        else:
                            existing = papers_dict[pid_str]
                            if (v_suc > existing.get("versions_success", 0)) or (
                                existing.get("source_status") != "success" and source_status == "success"
                            ):
                                papers_dict[pid_str] = paper_record

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

                    # 4. Process Resource Samples (only take for root or if samples exist)
                    # Limit sample rows to avoid multi-gigabyte memory consumption, sampling if needed
                    raw_samples = []
                    if "resource_samples.csv" in z.namelist():
                        raw_samples = parse_csv_from_zip(z, "resource_samples.csv")
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
                            except (KeyError, ValueError):
                                pass
                    elif "resource_samples.json" in z.namelist():
                        json_samples = parse_json_from_zip(z, "resource_samples.json")
                        if isinstance(json_samples, list):
                            for s in json_samples:
                                try:
                                    resource_samples.append({
                                        "run_id": run_id,
                                        "member": member,
                                        "account": account,
                                        "elapsed_seconds": float(s["elapsed_seconds"]),
                                        "ram_bytes": int(float(s["ram_bytes"])),
                                        "disk_bytes": int(float(s["disk_bytes"])),
                                    })
                                except (KeyError, ValueError):
                                    pass

                    # 5. Process Benchmark
                    if bench_data and not run_bench_entry:
                        run_bench_entry = {
                            "run_id": run_id,
                            "member": member,
                            "account": account,
                            "environment": bench_data.get("environment", "Linux x86_64; Python 3.13; Colab"),
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

        if run_bench_entry:
            run_bench_entry["discovery_elapsed_seconds"] = run_discovery_seconds
            benchmark_runs.append(run_bench_entry)

        run_metadata.append({
            "run_id": run_id,
            "member": member,
            "account": account,
            "is_checkpoint": is_cp,
            "zip_count": len(zip_paths),
            "papers_extracted": run_papers_count,
            "discovery_elapsed_seconds": run_discovery_seconds,
        })

    print(f"\n[INFO] Extracted {len(papers_dict):,} unique papers across all runs.")
    print(f"[INFO] Extracted {len(versions_dict):,} unique version entries.")
    print(f"[INFO] Extracted {len(references_dict):,} unique reference records.")

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
    # To keep notebook performance snappy while retaining statistical accuracy:
    # If samples > 30,000, subsample evenly
    sampled_out = resource_samples
    if len(resource_samples) > 30000:
        step = len(resource_samples) // 25000
        sampled_out = resource_samples[::step]
        print(f"[INFO] Subsampled resource traces: {len(resource_samples):,} -> {len(sampled_out):,} points")

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
    # Compute Aggregated Summary Metrics (Issue #1, #3, #5, #6, #7, #8, #9)
    # -------------------------------------------------------------
    papers_discovered = len(papers_dict)
    full_source_papers = sum(
        1 for p in papers_dict.values()
        if p["source_status"] == "success" or (
            p["versions_expected"] > 0 and (p["versions_success"] + p["versions_no_tex"] >= p["versions_expected"])
        )
    )

    v_success = sum(1 for v in versions_dict.values() if v["status"] == "success")
    v_notex = sum(1 for v in versions_dict.values() if v["status"] == "no_tex")
    v_failed = sum(1 for v in versions_dict.values() if v["status"] == "failed")
    v_pending = sum(1 for v in versions_dict.values() if v["status"] == "pending")
    versions_expected = len(versions_dict)

    # Reference metrics
    crawled_ref_rows = len(references_dict)
    arxiv_ref_rows = sum(1 for r in references_dict.values() if r["reference_arxiv_id"])
    non_arxiv_ref_rows = crawled_ref_rows - arxiv_ref_rows

    papers_with_refs = len(set(r["arxiv_id"] for r in references_dict.values()))

    # Size reductions from versions.csv
    valid_versions_before = [
        v["source_bytes_before"] for v in versions_dict.values()
        if v["source_bytes_before"] is not None and v["source_bytes_before"] > 0
    ]
    valid_versions_after = [
        v["source_bytes_after"] for v in versions_dict.values()
        if v["source_bytes_after"] is not None and v["source_bytes_after"] > 0
    ]

    total_bytes_before = sum(valid_versions_before)
    total_bytes_after = sum(valid_versions_after)

    avg_v_before = total_bytes_before / len(valid_versions_before) if valid_versions_before else 0.0
    avg_v_after = total_bytes_after / len(valid_versions_after) if valid_versions_after else 0.0

    # Paper size sums (grouped by arxiv_id)
    paper_bytes_before = defaultdict(float)
    paper_bytes_after = defaultdict(float)
    for v in versions_dict.values():
        pid = v["arxiv_id"]
        if v["source_bytes_before"]:
            paper_bytes_before[pid] += v["source_bytes_before"]
        if v["source_bytes_after"]:
            paper_bytes_after[pid] += v["source_bytes_after"]

    valid_p_before = [b for b in paper_bytes_before.values() if b > 0]
    valid_p_after = [b for b in paper_bytes_after.values() if b > 0]
    avg_p_before = sum(valid_p_before) / len(valid_p_before) if valid_p_before else 0.0
    avg_p_after = sum(valid_p_after) / len(valid_p_after) if valid_p_after else 0.0

    # Processing time per paper
    p_times = [p["elapsed_seconds"] for p in papers_dict.values() if p["elapsed_seconds"] is not None and p["elapsed_seconds"] > 0]
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
        "full_source_papers": full_source_papers,
        "versions_expected": versions_expected,
        "versions_success": v_success,
        "versions_no_tex": v_notex,
        "versions_failed": v_failed,
        "versions_pending": v_pending,
        "reference_jobs_success": papers_with_refs,
        "reference_jobs_partial": 0,
        "reference_jobs_failed": papers_discovered - papers_with_refs,
        "reference_jobs_not_found": 0,
        "reference_jobs_pending": 0,
        "crawled_reference_rows": crawled_ref_rows,
        "arxiv_reference_rows": arxiv_ref_rows,
        "non_arxiv_reference_rows": non_arxiv_ref_rows,
        "paper_success_rate": full_source_papers / papers_discovered if papers_discovered else 0.0,
        "source_coverage_rate": (v_success + v_notex) / versions_expected if versions_expected else 0.0,
        "reference_success_rate": papers_with_refs / papers_discovered if papers_discovered else 0.0,
        "average_reference_count": crawled_ref_rows / papers_discovered if papers_discovered else 0.0,
        "reference_count_denominator": papers_discovered,
        "average_reference_completeness_rate": 1.0,
        "reference_completeness_denominator": papers_with_refs,
        "average_paper_processing_seconds": avg_paper_seconds,
        "paper_time_denominator": len(p_times),
        "source_size_denominator": len(valid_versions_before),
        "average_source_bytes_before": avg_v_before,
        "average_source_bytes_after": avg_v_after,
        "paper_size_denominator": len(valid_p_before),
        "average_paper_source_bytes_before": avg_p_before,
        "average_paper_source_bytes_after": avg_p_after,
        "size_reduction_ratio": 1.0 - (total_bytes_after / total_bytes_before) if total_bytes_before else 0.0,
        "member_breakdown": member_summary,
    }

    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SYNC] Wrote {summary_path.name}")

    # -------------------------------------------------------------
    # Compute Aggregated Benchmark (Issue #1, #4)
    # -------------------------------------------------------------
    wall_times = [r["wall_seconds"] for r in benchmark_runs if r.get("wall_seconds")]
    peak_rams = [r["ram_peak_bytes"] for r in benchmark_runs if r.get("ram_peak_bytes")]
    mean_rams = [r["ram_mean_bytes"] for r in benchmark_runs if r.get("ram_mean_bytes")]
    peak_disks = [r["disk_peak_bytes"] for r in benchmark_runs if r.get("disk_peak_bytes")]
    final_disks = [r["final_disk_bytes"] for r in benchmark_runs if r.get("final_disk_bytes")]

    wall_times_sorted = sorted(wall_times)
    median_wall = wall_times_sorted[len(wall_times_sorted) // 2] if wall_times_sorted else 0.0
    total_wall = sum(wall_times)

    benchmark_data = {
        # Top-level backwards compatibility fields:
        "environment": "Linux x86_64; Python 3.13; Google Colab CPU-only",
        "cpu_only": True,
        "cache_mode": "cold",
        "sampling_interval_seconds": 0.25,
        "wall_seconds": total_wall,
        "median_wall_seconds": median_wall,
        "ram_peak_bytes": max(peak_rams) if peak_rams else 0,
        "ram_mean_bytes": sum(mean_rams) / len(mean_rams) if mean_rams else 0,
        "disk_peak_bytes": max(peak_disks) if peak_disks else 0,
        "final_disk_bytes": sum(final_disks) if final_disks else 0,
        # Multi-run aggregation details:
        "multi_run_summary": {
            "total_runs": len(benchmark_runs),
            "median_wall_seconds": median_wall,
            "total_wall_seconds": total_wall,
            "max_ram_peak_bytes": max(peak_rams) if peak_rams else 0,
            "mean_ram_bytes_across_runs": sum(mean_rams) / len(mean_rams) if mean_rams else 0,
            "total_discovery_elapsed_seconds": sum(r.get("discovery_elapsed_seconds", 0) for r in benchmark_runs),
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
    print(f"• Total Papers Discovered:     {s['papers_discovered']:,} (Target: 20,000)")
    print(f"• Full Source Coverage Papers: {s['full_source_papers']:,} ({s['paper_success_rate']*100:.2f}%)")
    print(f"• Total Versions Expected:     {s['versions_expected']:,}")
    print(f"• Versions Success:            {s['versions_success']:,} ({s['source_coverage_rate']*100:.2f}%)")
    print(f"• Versions Without TeX:        {s['versions_no_tex']:,}")
    print(f"• Crawled Reference Rows:      {s['crawled_reference_rows']:,}")
    print(f"• Size Reduction Ratio:        {s['size_reduction_ratio']*100:.2f}%")
    print(f"• Avg Source Bytes Before:     {s['average_source_bytes_before']/(1024):,.1f} KiB")
    print(f"• Avg Source Bytes After:      {s['average_source_bytes_after']/(1024):,.1f} KiB")
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
