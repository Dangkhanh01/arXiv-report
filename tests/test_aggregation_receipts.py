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

    def test_earlier_checkpoint_is_verified_too(self):
        path, receipt = self.archive(checkpoint="20261001T000000Z")
        self.archive(checkpoint="20261001T010000Z")
        receipt["archives"]["report"]["sha256"] = "0" * 64
        path.with_name("backup_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ingest()
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
