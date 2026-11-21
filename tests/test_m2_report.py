"""Regression cases for publication coverage and handoff denominators."""
import copy
import csv
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from aggregate_m2 import add_paper, validate_export, version_counts


class M2ReportTests(unittest.TestCase):
    def test_same_id_cannot_be_counted_in_two_runs(self):
        papers = {}
        add_paper(papers, "2606.15734", {"run_id": "first"})
        with self.assertRaisesRegex(ValueError, "Duplicate publication"):
            add_paper(papers, "2606.15734", {"run_id": "second"})
        self.assertEqual(papers["2606.15734"]["run_id"], "first")

    def test_partial_output_and_expected_empty_have_separate_denominators(self):
        counts = version_counts({"1": "parsed", "2": "partial", "3": "empty_no_tex"})
        self.assertEqual(counts["parsed"], 1)
        self.assertEqual(counts["parsed"] + counts["partial"], 2)
        self.assertEqual(sum(counts.values()), 3)

    def test_handoff_excludes_working_rows_from_ineligible_papers(self):
        papers = {
            "2606.00001": dict(export_ready=True, elements_after_dedup=2,
                               hierarchy_edges=1, bibtex_entries_after_dedup=1),
            "2606.00002": dict(export_ready=False, elements_after_dedup=8,
                               hierarchy_edges=7, bibtex_entries_after_dedup=2),
        }
        manifest = dict(excluded=[dict(arxiv_id="2606-00002", reason="partial_version")],
                        publications_excluded=1, publications_included=1, publications_expected=2,
                        rows=dict(elements=2, hierarchy=1, bibtex=1))
        validate_export(papers, manifest)
        self.assertEqual(papers["2606.00002"]["exclusion_reason"], "partial_version")
        wrong = copy.deepcopy(manifest)
        wrong["rows"]["elements"] = 10
        with self.assertRaisesRegex(ValueError, "Export-ready elements"):
            validate_export(papers, wrong)

    def test_report_rows_reconcile_with_m1_and_handoff_inventory(self):
        def rows(relative):
            with (ROOT / "book" / relative).open(encoding="utf-8", newline="") as stream:
                return list(csv.DictReader(stream))

        papers = rows("data_m2/papers.csv")
        versions = rows("data_m2/versions.csv")
        runs = rows("data_m2/runs.csv")
        m1_keys = [(r["arxiv_id"], r["version"]) for r in rows("data/versions.csv")]
        self.assertCountEqual(((r["arxiv_id"], r["version"]) for r in versions), m1_keys)
        self.assertEqual(len({r["arxiv_id"] for r in papers}), 20000)
        self.assertEqual(len(papers), 20000)
        self.assertEqual(len({r["run_id"] for r in runs}), 12)
        self.assertEqual(Counter(r["exclusion_reason"] for r in papers),
                         {"": 18902, "unresolved_citations": 717, "partial_version": 260,
                          "gate_not_passed": 110, "failed_version": 11})
        self.assertEqual(sum(r["status"] == "parsed" for r in versions), 25037)
        self.assertEqual(sum(int(r["elements_rows"]) for r in runs), 8900012)
