"""Exercise report ingestion against real ZIPs and crawler backup receipts."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("aggregate_data", ROOT / "scripts/aggregate_data.py")
aggregate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregate)
RUN = "00000000-0000-0000-0000-000000000001"


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "book/_build").mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "book/_build")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "input"
        self.target = self.root / "output"

    def archive(self, run=RUN, checkpoint=None):
        base = self.source / "Danh/acc1/Milestone1"
        folder = base / run / "attempt" if checkpoint is None else base / "checkpoints" / run / checkpoint
        folder.mkdir(parents=True)
        path = folder / "report.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("manifest.json", json.dumps({
                "run_id": run,
                "discovery": {"elapsed_seconds": 1},
                "papers": {"2606.15734": {"record": {"metadata": {
                    "title": "Fixture", "submission_date": "2026-06-14"
                }}}}
            }))
            archive.writestr("papers.csv", "arxiv_id,reference_status,versions_expected,total_references,kept_references,elapsed_seconds\n2606.15734,success,1,0,0,2\n")
            archive.writestr("versions.csv", "arxiv_id,version,status,source_bytes_before,source_bytes_after\n2606.15734,1,success,100,20\n")
            archive.writestr("benchmark.json", json.dumps({"wall_seconds": 3}))
        receipt = {"run_id": run, "archives": {"report": {
            "filename": "report.zip", "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        }}}
        (folder / "backup_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return path, receipt

    def ingest(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return aggregate.aggregate_corpus(self.source, self.target)

    def test_valid_receipt_accepts_report(self):
        self.archive()
        result = self.ingest()
        self.assertEqual(result["summary"]["papers_discovered"], 1)
        self.assertIsNone(result["benchmark"]["cpu_only"])
        self.assertIn("unknown", result["benchmark"]["cache_mode"])
        metadata = json.loads((self.target / "run_metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata[0]["verified_archives"][0]["verified"])

    def test_bad_receipts_reject_before_replacing_existing_data(self):
        path, valid = self.archive()
        self.target.mkdir()
        sentinel = self.target / "summary.json"
        sentinel.write_text('{"previous": true}', encoding="utf-8")
        mutations = {
            "wrong digest": lambda r: r["archives"]["report"].update(sha256="0" * 64),
            "missing digest": lambda r: r["archives"]["report"].pop("sha256"),
            "malformed digest": lambda r: r["archives"]["report"].update(sha256="invalid"),
            "wrong size": lambda r: r["archives"]["report"].update(bytes=1),
            "wrong run": lambda r: r.update(run_id="another-run"),
            "wrong filename": lambda r: r["archives"]["report"].update(filename="other.zip"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                receipt = json.loads(json.dumps(valid))
                mutate(receipt)
                path.with_name("backup_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.ingest()
                self.assertEqual(sentinel.read_text(encoding="utf-8"), '{"previous": true}')

    def test_missing_receipt_rejects_report(self):
        path, _ = self.archive()
        path.with_name("backup_receipt.json").unlink()
        with self.assertRaises(ValueError):
            self.ingest()

    def test_missing_completeness_evidence_stays_unknown(self):
        self.archive()
        result = self.ingest()
        self.assertIsNone(result["summary"]["average_reference_completeness_rate"])
        self.assertEqual(result["summary"]["reference_completeness_denominator"], 0)

    def test_unlisted_expected_version_is_not_source_success(self):
        path, receipt = self.archive()
        with zipfile.ZipFile(path) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries["papers.csv"] = entries["papers.csv"].replace(b",success,1,0,0,2", b",success,2,0,0,2")
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        receipt["archives"]["report"].update(
            bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        path.with_name("backup_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        result = self.ingest()
        self.assertEqual(result["summary"]["full_tex_papers"], 0)
        self.assertEqual(result["summary"]["unresolved_source_papers"], 1)
        self.assertEqual(result["summary"]["versions_expected"], 2)
        self.assertEqual(result["summary"]["source_coverage_rate"], 0.5)

    def test_earlier_checkpoint_is_verified_too(self):
        path, receipt = self.archive(checkpoint="20261001T000000Z")
        self.archive(checkpoint="20261001T010000Z")
        receipt["archives"]["report"]["sha256"] = "0" * 64
        path.with_name("backup_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ingest()
        self.assertFalse(self.target.exists())


class CorpusInvariantTests(unittest.TestCase):
    """Verify data invariants on the generated datasets in book/data/."""

    def test_references_invariants(self):
        import csv
        csv_path = ROOT / "book/data/papers_detail.csv"
        self.assertTrue(csv_path.is_file(), "papers_detail.csv must exist")
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            partial_ids = {"2602.01405", "2602.00562", "2602.01397"}
            for row in reader:
                aid = row["arxiv_id"]
                tot = row["total_references"]
                kept = int(row["kept_references"])
                if aid in partial_ids:
                    self.assertEqual(row["reference_status"], "partial")
                    self.assertEqual(tot, "", f"Partial paper {aid} must have empty total_references")
                    self.assertGreater(kept, 0)
                elif tot != "":
                    self.assertLessEqual(kept, int(tot), f"Kept refs must not exceed total for {aid}")

    def test_histogram_coverage_reaches_full_corpus(self):
        import pandas as pd
        csv_path = ROOT / "book/data/papers_detail.csv"
        df = pd.read_csv(csv_path)
        s_tot = pd.to_numeric(df["total_references"], errors="coerce")
        ref_bins = pd.cut(
            s_tot.dropna(),
            bins=[-1, 0, 10, 25, 50, 100, float("inf")],
            labels=["0 refs", "1-10 refs", "11-25 refs", "26-50 refs", "51-100 refs", ">100 refs"]
        )
        dist = ref_bins.value_counts()
        partial_count = int(s_tot.isna().sum())
        total_accounted = dist.sum() + partial_count
        self.assertEqual(total_accounted, 20000, "Histogram bins plus partials must account for exactly 20,000 papers")
        # Paper 2602.19887 with 1002 refs must be in >100 refs bin
        self.assertGreater(dist[">100 refs"], 0)

    def test_summary_schema_and_kpis(self):
        summary_path = ROOT / "book/data/summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        required_keys = [
            "papers_discovered", "full_tex_papers", "full_tex_paper_rate",
            "resolved_source_papers", "resolved_source_rate", "unresolved_source_papers",
            "versions_expected", "versions_success", "versions_no_tex", "versions_failed",
            "total_extracted_references_confirmed", "arxiv_reference_rows", "non_arxiv_reference_rows",
            "selected_runs_total", "benchmark_runs_total", "member_breakdown"
        ]
        for k in required_keys:
            self.assertIn(k, summary, f"summary.json missing required key: {k}")
        self.assertEqual(summary["papers_discovered"], 20000)
        self.assertEqual(summary["selected_runs_total"], 75)
        self.assertEqual(summary["benchmark_runs_total"], 107)

    def test_cpu_only_and_provenance_full_coverage(self):
        bench_path = ROOT / "book/data/benchmark.json"
        bench = json.loads(bench_path.read_text(encoding="utf-8"))
        self.assertIs(bench["cpu_only"], True, "Top-level cpu_only must be True")
        runs = bench["runs"]
        self.assertEqual(len(runs), 107, "Must document 107 benchmark runs")
        self.assertTrue(all(r.get("cpu_only") is True for r in runs), "All 107 runs must be CPU-only")

        meta_path = ROOT / "book/data/run_metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(len(meta), 107, "Must document 107 metadata run entries")
        for r in meta:
            self.assertTrue(r.get("verified_archives"), f"Run {r['run_id']} must have verified_archives")
            self.assertTrue(all(a.get("verified") is True for a in r["verified_archives"]))

    def test_member_breakdown_alignment(self):
        summary_path = ROOT / "book/data/summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        mb = summary["member_breakdown"]
        tot_selected = sum(data["selected_runs_count"] for data in mb.values())
        tot_bench = sum(data["benchmark_runs_count"] for data in mb.values())
        self.assertEqual(tot_selected, 75, "Sum of selected paper runs must be 75")
        self.assertEqual(tot_bench, 107, "Sum of benchmark runs must be 107")


if __name__ == "__main__":
    unittest.main()
