#!/usr/bin/env python3
"""sync_data.py — Data Synchronization & Aggregation Utility for arXiv Report.

This script syncs experimental measurements and crawl metrics from Google Colab /
Google Drive run backups (or aggregated multi-member trees) into `book/data/`
for dynamic Jupyter Book compilation.

Usage:
  python scripts/sync_data.py [--source PATH] [--build]

Examples:
  # Auto-detect Milestone1 folder from workspace root
  python scripts/sync_data.py

  # Specify a custom path (e.g. from Google Drive or full aggregated 20k-paper tree)
  python scripts/sync_data.py --source /path/to/Milestone1

  # Sync and immediately rebuild the Jupyter Book
  python scripts/sync_data.py --build
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


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_default_source() -> Path:
    """Locate the Milestone1 directory in standard locations."""
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root.parent / "Milestone1",
        repo_root / "data/Milestone1",
        Path.cwd() / "Milestone1",
        Path.cwd().parent / "Milestone1",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def find_latest_report_zip(source_dir: Path) -> tuple[Path, Path]:
    """Find the most comprehensive report.zip and its backup_receipt.json in source_dir."""
    report_zips = list(source_dir.rglob("report.zip"))
    if not report_zips:
        raise FileNotFoundError(f"No report.zip found inside {source_dir}")

    # Prioritize the largest report.zip or latest timestamp
    report_zips.sort(key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    best_zip = report_zips[0]

    receipt_file = best_zip.parent / "backup_receipt.json"
    if not receipt_file.is_file():
        receipt_file = None

    return best_zip, receipt_file


def verify_receipt(report_zip: Path, receipt_file: Path) -> bool:
    """Verify SHA-256 checksum against backup_receipt.json if available."""
    if not receipt_file or not receipt_file.is_file():
        print(f"[WARN] No backup_receipt.json found for {report_zip.name}. Skipping hash check.")
        return True

    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    expected = receipt.get("archives", {}).get("report", {})
    expected_hash = expected.get("sha256")
    expected_size = expected.get("bytes")

    actual_size = report_zip.stat().st_size
    if expected_size and actual_size != expected_size:
        raise ValueError(f"Size mismatch for {report_zip}: expected {expected_size}, got {actual_size}")

    actual_hash = sha256_file(report_zip)
    if expected_hash and actual_hash != expected_hash:
        raise ValueError(f"Hash mismatch for {report_zip}: expected {expected_hash}, got {actual_hash}")

    print(f"[OK] Verified SHA-256 integrity: {actual_hash[:16]}...")
    return True


def sync_from_zip(report_zip: Path, target_dir: Path) -> dict:
    """Extract required metric files from report.zip into book/data/."""
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted_summary = {}

    with zipfile.ZipFile(report_zip, "r") as z:
        namelist = set(z.namelist())

        # 1. summary.json
        if "summary.json" in namelist:
            summary_content = z.read("summary.json")
            (target_dir / "summary.json").write_bytes(summary_content)
            extracted_summary["summary"] = json.loads(summary_content)
            print("[SYNC] Extracted summary.json")

        # 2. benchmark.json
        if "benchmark.json" in namelist:
            bench_content = z.read("benchmark.json")
            (target_dir / "benchmark.json").write_bytes(bench_content)
            extracted_summary["benchmark"] = json.loads(bench_content)
            print("[SYNC] Extracted benchmark.json")

        # 3. resource_samples.csv
        if "resource_samples.csv" in namelist:
            samples_content = z.read("resource_samples.csv")
            (target_dir / "resource_samples.csv").write_bytes(samples_content)
            print("[SYNC] Extracted resource_samples.csv")

        # 4. papers_unique.csv (enriched from manifest.json or papers.csv)
        if "manifest.json" in namelist:
            manifest = json.loads(z.read("manifest.json"))
            member_name = "Danh"
            # Attempt to find owner member from retry-state if present
            try:
                for state_file in report_zip.parents[2].glob("retry-state/member-*.json"):
                    s_data = json.loads(state_file.read_text(encoding="utf-8"))
                    if "member" in s_data:
                        member_name = s_data["member"]
                        break
            except Exception:
                pass

            rows = []
            for arxiv_id, p_info in manifest.get("papers", {}).items():
                rec = p_info.get("record", {})
                meta = rec.get("metadata", {}) if isinstance(rec, dict) else {}
                rows.append({
                    "member": member_name,
                    "arxiv_id": arxiv_id,
                    "title": meta.get("title", ""),
                    "submission_date": meta.get("submission_date", "")
                })

            with open(target_dir / "papers_unique.csv", "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["member", "arxiv_id", "title", "submission_date"])
                writer.writeheader()
                writer.writerows(rows)
            print(f"[SYNC] Generated papers_unique.csv ({len(rows)} papers with title & submission_date)")
        elif "papers_unique.csv" in namelist:
            papers_content = z.read("papers_unique.csv")
            (target_dir / "papers_unique.csv").write_bytes(papers_content)
            print("[SYNC] Extracted papers_unique.csv")
        elif "papers.csv" in namelist:
            papers_content = z.read("papers.csv")
            (target_dir / "papers_unique.csv").write_bytes(papers_content)
            print("[SYNC] Extracted papers.csv -> papers_unique.csv")

    return extracted_summary


def sync_aggregated_tree(source_dir: Path, target_dir: Path) -> dict:
    """Sync directly from an aggregated output directory if pre-computed."""
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted_summary = {}

    for fname in ["summary.json", "benchmark.json", "resource_samples.csv", "papers_unique.csv"]:
        src_file = source_dir / fname
        if src_file.is_file():
            shutil.copy2(src_file, target_dir / fname)
            print(f"[SYNC] Copied {fname} from aggregated source")
            if fname.endswith(".json"):
                extracted_summary[fname.replace(".json", "")] = json.loads(src_file.read_text(encoding="utf-8"))

    return extracted_summary


def main():
    parser = argparse.ArgumentParser(description="Synchronize crawler measurements into Jupyter Book data directory.")
    parser.add_argument("--source", type=str, default=None, help="Path to Milestone1 run directory or aggregated metrics folder.")
    parser.add_argument("--target", type=str, default=None, help="Destination directory (default: book/data).")
    parser.add_argument("--build", action="store_true", help="Rebuild the Jupyter Book immediately after sync.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target_dir = Path(args.target) if args.target else repo_root / "book/data"

    if args.source:
        source_dir = Path(args.source).resolve()
    else:
        source_dir = find_default_source()
        if not source_dir:
            print("[ERROR] Could not auto-detect Milestone1 directory. Please specify with --source <PATH>")
            sys.exit(1)

    print(f"=== arXiv Report Data Sync Utility ===")
    print(f"Source Directory: {source_dir}")
    print(f"Target Directory: {target_dir}")

    # Check if source_dir already has ready-to-use CSV/JSON files
    if (source_dir / "summary.json").is_file() and (source_dir / "papers_unique.csv").is_file():
        print("[INFO] Detected pre-aggregated directory.")
        metrics = sync_aggregated_tree(source_dir, target_dir)
    else:
        print("[INFO] Scanning for durable report archives (report.zip)...")
        best_zip, receipt_file = find_latest_report_zip(source_dir)
        print(f"[FOUND] Latest report archive: {best_zip} ({best_zip.stat().st_size:,} bytes)")
        verify_receipt(best_zip, receipt_file)
        metrics = sync_from_zip(best_zip, target_dir)

    # Print summary highlights
    print("\n--- Ingested Metrics Audit ---")
    summary = metrics.get("summary", {})
    bench = metrics.get("benchmark", {})
    if summary:
        print(f"• Papers Discovered:   {summary.get('papers_discovered', 'N/A'):,}")
        print(f"• Full Source Papers:  {summary.get('full_source_papers', 'N/A'):,}")
        print(f"• Total Versions:      {summary.get('versions_expected', 'N/A'):,}")
        print(f"• Reference Rows:      {summary.get('crawled_reference_rows', 'N/A'):,}")
        print(f"• Source Coverage:     {summary.get('source_coverage_rate', 0)*100:.2f}%")
    if bench:
        print(f"• Wall Clock Time:     {bench.get('wall_seconds', 0):,.1f} s")
        print(f"• Peak RAM:            {bench.get('ram_peak_bytes', 0)/(1024**2):.2f} MB")
        print(f"• Environment:         {bench.get('environment', 'N/A')}")
    print("------------------------------")
    print(f"[SUCCESS] All target datasets in {target_dir} updated successfully!")

    if args.build:
        print("\n=== Building Jupyter Book ===")
        venv_jb = repo_root / ".venv/Scripts/jupyter-book.exe"
        jb_cmd = str(venv_jb) if venv_jb.is_file() else "jupyter-book"
        res = subprocess.run([jb_cmd, "build", "--all", str(repo_root / "book")], check=False)
        if res.returncode == 0:
            print("[SUCCESS] Jupyter Book rebuild completed cleanly.")
        else:
            print(f"[FAIL] Jupyter Book build exited with code {res.returncode}")
            sys.exit(res.returncode)


if __name__ == "__main__":
    main()
