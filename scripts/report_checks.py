"""Shared build-time validation; report notebooks must not hide missing inputs."""
import csv
import json
import math
from pathlib import Path

from aggregate_data import assignment_coverage

SUMMARY_NUMERIC = (
    'papers_discovered', 'full_tex_papers', 'full_tex_paper_rate',
    'resolved_source_papers', 'resolved_source_rate', 'unresolved_source_papers',
    'versions_expected', 'versions_success', 'versions_no_tex', 'versions_failed',
    'versions_pending', 'versions_missing', 'source_coverage_rate',
    'total_extracted_references_confirmed', 'arxiv_reference_rows', 'non_arxiv_reference_rows',
    'reference_jobs_success', 'reference_api_success_rate', 'papers_with_arxiv_pool',
    'papers_with_arxiv_pool_rate', 'average_reference_count_confirmed',
    'paired_tex_versions_count', 'average_tex_source_bytes_before',
    'average_tex_source_bytes_after', 'tex_size_reduction_ratio',
    'average_source_bytes_before', 'average_source_bytes_after', 'source_size_denominator',
    'size_reduction_ratio', 'average_paper_source_bytes_before',
    'average_paper_source_bytes_after', 'paper_size_denominator',
    'average_paper_processing_seconds', 'paper_time_denominator',
    'selected_runs_total', 'benchmark_runs_total', 'id_discovery_coverage',
    'assigned_ids_target', 'missing_assigned_ids_count', 'unexpected_ids_count', 'reference_count_denominator',
    'invalid_assigned_metadata_count', 'wrong_member_ids_count', 'observed_reference_lower_bound',
)
SUMMARY_OPTIONAL = ('total_extracted_references_observed', 'average_reference_count_observed')
BENCH_NUMERIC = ('wall_seconds', 'median_wall_seconds', 'ram_peak_bytes', 'ram_mean_bytes',
                 'disk_peak_bytes', 'sum_run_final_disk_bytes', 'merged_corpus_tex_bib_bytes')


def require_fields(data, numeric=(), present=()):
    missing = (set(numeric) | set(present)) - set(data)
    if missing:
        raise ValueError(f'Missing required fields: {sorted(missing)}')
    for key in numeric:
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Invalid numeric KPI {key}: {value!r}')


def load_report_data(data_dir):
    data_dir = Path(data_dir)
    summary = json.loads((data_dir / 'summary.json').read_text(encoding='utf-8'))
    bench = json.loads((data_dir / 'benchmark.json').read_text(encoding='utf-8'))
    require_fields(summary, SUMMARY_NUMERIC, SUMMARY_OPTIONAL + ('member_breakdown', 'metadata_field_audit', 'assigned_member_targets'))
    require_fields(bench, tuple(k for k in BENCH_NUMERIC if bench.get(k) is not None), BENCH_NUMERIC + ('runs', 'multi_run_summary', 'merged_corpus_uncompressed_bytes',
                                        'merged_corpus_file_count', 'cpu_only', 'merged_corpus_measurement_status'))
    for key in SUMMARY_OPTIONAL:
        if summary[key] is not None:
            require_fields(summary, (key,))
    def rows(name):
        with (data_dir / name).open(encoding='utf-8', newline='') as stream:
            return list(csv.DictReader(stream))
    detail = rows('papers_detail.csv')
    unique = rows('papers_unique.csv')
    versions = rows('versions.csv')
    papers = {r['arxiv_id']: r for r in detail}
    if len(papers) != len(detail) or {r['arxiv_id'] for r in unique} != set(papers) or len(unique) != len(detail):
        raise ValueError('Duplicate/mismatched paper tables')
    actual_coverage = assignment_coverage(papers)
    for key, value in actual_coverage.items():
        if summary.get(key) != value:
            raise ValueError(f'Assignment summary mismatch: {key}')
    if summary['papers_discovered'] != len(detail):
        raise ValueError('Paper count mismatch')
    known = [r for r in detail if r['total_references'] != '']
    total = sum(int(r['total_references']) for r in known)
    if total != summary['total_extracted_references_confirmed'] or len(known) != summary['reference_count_denominator']:
        raise ValueError('Reference confirmed count/denominator mismatch')
    for row in detail:
        kept = int(row['kept_references'])
        if kept < 0 or (row['total_references'] and kept > int(row['total_references'])):
            raise ValueError('Reference subset/total invariant failed')
    if sum(int(r['kept_references']) for r in detail) != summary['arxiv_reference_rows']:
        raise ValueError('Reference pool counter mismatch')
    if total - sum(int(r['kept_references']) for r in known) != summary['non_arxiv_reference_rows']:
        raise ValueError('Confirmed non-arXiv counter mismatch')
    if not math.isclose(total / len(known) if known else 0, summary['average_reference_count_confirmed']):
        raise ValueError('Reference mean mismatch')
    keys = {(r['arxiv_id'], r['version']) for r in versions}
    if len(keys) != len(versions) or any(r['arxiv_id'] not in papers for r in versions):
        raise ValueError('Duplicate/orphan version records')
    if len(versions) + summary['versions_missing'] != summary['versions_expected']:
        raise ValueError('Expected/observed/missing version count mismatch')
    for status in ('success', 'no_tex', 'failed', 'pending'):
        if sum(r['status'] == status for r in versions) != summary[f'versions_{status}']:
            raise ValueError(f'Version status mismatch: {status}')
    metadata = json.loads((data_dir / 'run_metadata.json').read_text(encoding='utf-8'))
    runs = bench['runs']
    if len({r['run_id'] for r in runs}) != len(runs) or {r['run_id'] for r in runs} != {r['run_id'] for r in metadata}:
        raise ValueError('Benchmark/provenance run mismatch')
    if len(runs) != summary['benchmark_runs_total'] or len({r['run_id'] for r in detail}) != summary['selected_runs_total']:
        raise ValueError('Run count mismatch')
    for member, stats in summary['member_breakdown'].items():
        selected = [r for r in detail if r['member'] == member]
        if stats['papers'] != len(selected) or stats['selected_runs_count'] != len({r['run_id'] for r in selected}) or stats['benchmark_runs_count'] != sum(r['member'] == member for r in runs):
            raise ValueError(f'Member summary mismatch: {member}')
    return summary, bench


def reference_distribution(frame):
    """Use the same checked binning in the Book and regression tests."""
    import pandas as pd
    totals = pd.to_numeric(frame['total_references'], errors='raise')
    known = totals.dropna()
    if (known < 0).any() or (known % 1 != 0).any():
        raise ValueError('Invalid reference totals')
    binned = pd.cut(known, [-1, 0, 10, 25, 50, 100, float('inf')],
                    labels=['0 refs', '1–10 refs', '11–25 refs', '26–50 refs', '51–100 refs', '>100 refs'])
    distribution = binned.value_counts().sort_index().astype('int64')
    # Convert the categorical index before adding explicit unknown outcomes.
    distribution.index = distribution.index.astype(str)
    for status, count in frame.loc[totals.isna(), 'reference_status'].value_counts().items():
        distribution.loc[f'Unknown total ({status})'] = int(count)
    if int(distribution.sum()) != len(frame):
        raise ValueError('Histogram does not cover the input population')
    return distribution
