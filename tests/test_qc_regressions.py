"""Behavioral regressions for QC, using real receipt-verified ZIP fixtures."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
import test_aggregation_receipts as fixtures
RUN, ROOT, aggregate = fixtures.RUN, fixtures.ROOT, fixtures.aggregate
sys.path.insert(0, str(ROOT / 'scripts'))
from report_checks import load_report_data, reference_distribution, require_fields


class AggregationRegressions(unittest.TestCase):
    setUp = fixtures.ReceiptTests.setUp
    archive = fixtures.ReceiptTests.archive
    ingest = fixtures.ReceiptTests.ingest

    def rewrite(self, path, receipt, edit):
        with zipfile.ZipFile(path) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        edit(entries)
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in entries.items(): archive.writestr(name, data)
        receipt['archives']['report'].update(bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        path.with_name('backup_receipt.json').write_text(json.dumps(receipt))

    def sentinel(self):
        self.target.mkdir()
        for name in ('papers_unique.csv', 'summary.json', 'versions.csv'):
            (self.target / name).write_text('old ' + name)
        return {p.name: p.read_bytes() for p in self.target.iterdir()}

    def assert_unchanged(self, before):
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, before)

    def test_incomplete_coverage_and_absent_corpus_not_fabricated(self):
        self.archive()
        result = self.ingest()
        self.assertEqual(result['summary']['missing_assigned_ids_count'], 19999)
        self.assertEqual(result['summary']['id_discovery_coverage'], 1 / 20000)
        self.assertIsNone(result['benchmark']['merged_corpus_uncompressed_bytes'])
        self.assertIsNone(result['benchmark']['merged_corpus_file_count'])

    def test_missing_resource_measurements_remain_unknown(self):
        self.archive()
        bench = self.ingest()['benchmark']
        self.assertIsNone(bench['ram_peak_bytes'])
        self.assertIsNone(bench['ram_mean_bytes'])
        self.assertIsNone(bench['disk_peak_bytes'])
        self.assertIsNone(bench['sum_run_final_disk_bytes'])
        self.assertEqual(bench['measurement_run_counts']['ram_peak_bytes'], 0)

    def test_invalid_counter_and_csv_row_reject_before_publish(self):
        path, receipt = self.archive()
        before = self.sentinel()
        for count in ('-1', '1.5', 'NaN', 'Infinity'):
            def edit(e):
                e['papers.csv'] = f'arxiv_id,reference_status,versions_expected,total_references,kept_references\n2606.15734,success,{count},0,0\n'.encode()
            self.rewrite(path, receipt, edit)
            with self.subTest(count=count):
                with self.assertRaises(ValueError): self.ingest()
                self.assert_unchanged(before)
        self.rewrite(path, receipt, lambda e:e.update({'papers.csv':b'arxiv_id,versions_expected,reference_status,total_references,kept_references\n2606.15734,1,success,0,0,EXTRA\n'}))
        with self.assertRaises(ValueError): self.ingest()
        self.assert_unchanged(before)


    def test_unexpected_id_does_not_increase_coverage(self):
        paper = dict(member='Danh', title='Valid', submission_date='2026-06-14')
        result = aggregate.assignment_coverage({'9999.00001': paper})
        self.assertEqual(result['id_discovery_coverage'], 0)
        self.assertEqual(result['missing_assigned_ids_count'], 20000)
        self.assertEqual(result['unexpected_ids_count'], 1)

    def test_checkpoint_expected_growth(self):
        self.archive(checkpoint='20261001T000000Z')
        path, receipt = self.archive(checkpoint='20261001T010000Z')
        def edit(e):
            e['papers.csv'] = e['papers.csv'].replace(b',success,1,0,0,2', b',success,3,0,0,2')
            e['versions.csv'] += b'2606.15734,2,success,100,20\n'
        self.rewrite(path, receipt, edit)
        summary = self.ingest()['summary']
        self.assertEqual(summary['versions_expected'], 3)
        self.assertEqual(summary['versions_missing'], 1)
        self.assertEqual(summary['full_tex_papers'], 0)
        self.assertEqual(summary['unresolved_source_papers'], 1)

    def test_non_arxiv_fallback_excluded_from_pool(self):
        path, receipt = self.archive()
        def edit(e):
            e['papers.csv'] = e['papers.csv'].replace(b',success,1,0,0,2', b',success,1,1,0,2')
            e['references_all.csv'] = b'arxiv_id,reference_arxiv_id,title\n2606.15734,,Book\n'
        self.rewrite(path, receipt, edit)
        summary = self.ingest()['summary']
        self.assertEqual(summary['arxiv_reference_rows'], 0)
        self.assertEqual(summary['papers_with_arxiv_pool'], 0)
        self.assertEqual(summary['non_arxiv_reference_rows'], 1)

    def test_partial_rows_counted_and_not_double_counted(self):
        path, receipt = self.archive()
        for total in ('', '7'):
            with self.subTest(total=total):
                def edit(e):
                    e['papers.csv'] = f'arxiv_id,reference_status,versions_expected,total_references,kept_references,elapsed_seconds\n2606.15734,partial,1,{total},0,2\n'.encode()
                    e['references_all.csv'] = b'arxiv_id,reference_arxiv_id,title\n' + b'2606.15734,,Book\n' * 7
                self.rewrite(path, receipt, edit)
                summary = self.ingest()['summary']
                self.assertEqual(summary['total_extracted_references_observed'], 7)
                self.assertEqual(summary['observed_reference_lower_bound'], 7)

    def test_partial_without_store_stays_unknown(self):
        path, receipt = self.archive()
        self.rewrite(path, receipt, lambda e:e.update({'papers.csv':e['papers.csv'].replace(b',success,1,0,0,2', b',partial,1,,0,2')}))
        summary = self.ingest()['summary']
        self.assertIsNone(summary['total_extracted_references_observed'])
        self.assertIsNone(summary['average_reference_count_observed'])

    def test_invalid_manifest_rejects_without_mutation(self):
        path, receipt = self.archive()
        with zipfile.ZipFile(path) as archive: original = archive.read('manifest.json')
        before = self.sentinel()
        for value in (None, b'{broken', b'[]', original.replace(RUN.encode(), b'WRONG-RUN')):
            with self.subTest(value=value):
                def edit(e):
                    if value is None: e.pop('manifest.json', None)
                    else: e['manifest.json'] = value
                self.rewrite(path, receipt, edit)
                with self.assertRaises(ValueError): self.ingest()
                self.assert_unchanged(before)

    def test_invariant_failure_preserves_entire_target(self):
        path, receipt = self.archive()
        self.rewrite(path, receipt, lambda e:e.update({'papers.csv':e['papers.csv'].replace(b',success,1,0,0,2', b',success,1,0,1,2')}))
        before = self.sentinel()
        with self.assertRaises(ValueError): self.ingest()
        self.assert_unchanged(before)

    def test_empty_input_preserves_target(self):
        self.source.mkdir()
        before = self.sentinel()
        with self.assertRaises(ValueError): self.ingest()
        self.assert_unchanged(before)

    def test_publication_failure_rolls_back(self):
        self.archive()
        before = self.sentinel()
        replace = aggregate.os.replace
        def fail_publication(src, dst):
            if Path(src).name == 'snapshot': raise OSError('injected publication failure')
            return replace(src, dst)
        with patch.object(aggregate.os, 'replace', side_effect=fail_publication):
            with self.assertRaises(OSError): self.ingest()
        self.assert_unchanged(before)

    def test_corpus_verification_separate_and_bad_corpus_rejected(self):
        path, receipt = self.archive()
        corpus = path.with_name('corpus.zip')
        with zipfile.ZipFile(corpus, 'w') as archive: archive.writestr('paper/main.tex', 'test')
        receipt['archives']['corpus'] = dict(filename='corpus.zip', bytes=corpus.stat().st_size,
            sha256=hashlib.sha256(corpus.read_bytes()).hexdigest())
        path.with_name('backup_receipt.json').write_text(json.dumps(receipt))
        self.assertEqual(self.ingest()['benchmark']['verified_corpus_archive_count'], 1)
        meta = json.loads((self.target/'run_metadata.json').read_text())
        self.assertEqual(meta[0]['verified_corpus_archives'][0]['kind'], 'corpus')
        before = {p.name:p.read_bytes() for p in self.target.iterdir()}
        corpus.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.ingest()
        self.assert_unchanged(before)

    def test_pool_uses_selected_snapshot_not_union(self):
        for i, status in enumerate(('partial', 'success')):
            path, receipt = self.archive(checkpoint=f'20261001T0{i}0000Z')
            def edit(e):
                e['papers.csv'] = e['papers.csv'].replace(b',success,1,0,0,2', f',{status},1,1,1,2'.encode())
                e['references.csv'] = f'arxiv_id,reference_arxiv_id,title\n2606.15734,2601.0000{i},Example\n'.encode()
            self.rewrite(path, receipt, edit)
        self.assertEqual(self.ingest()['summary']['arxiv_reference_rows'], 1)
        with (self.target/'references_agg.csv').open() as stream: rows=list(csv.DictReader(stream))
        self.assertEqual(rows[0]['reference_arxiv_id'], '2601.00001')


class BookRegressions(unittest.TestCase):
    def test_committed_report_consistency(self):
        load_report_data(ROOT/'book/data')

    def test_missing_invalid_kpi_rejected(self):
        with self.assertRaises(ValueError): require_fields({}, ('needed',))
        for value in (None, -1, float('nan'), True, '123'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): require_fields({'needed':value}, ('needed',))

    def test_shared_histogram_handles_outlier_and_unknowns(self):
        import pandas as pd
        frame = pd.DataFrame({'total_references':[1002,0,None,None], 'reference_status':['success','success','partial','not_found']})
        dist = reference_distribution(frame)
        self.assertEqual(dist['>100 refs'], 1)
        self.assertEqual(dist['Unknown total (partial)'], 1)
        self.assertEqual(dist['Unknown total (not_found)'], 1)
        self.assertEqual(dist.sum(), 4)

    def test_unverified_claims_not_fabricated(self):
        summary, bench = load_report_data(ROOT/'book/data')
        self.assertIsNone(summary['total_extracted_references_observed'])
        self.assertEqual(summary['observed_reference_lower_bound'], 734320)
        self.assertIsNone(bench['merged_corpus_uncompressed_bytes'])
        self.assertEqual(summary['metadata_field_audit']['paper_fields']['authors']['audited'], 0)


if __name__ == '__main__': unittest.main()
