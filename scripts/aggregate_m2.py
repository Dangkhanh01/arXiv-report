"""Build compact Milestone 2 report inputs from the twelve full-corpus exports."""
import argparse
import csv
import gzip
import json
import re
import tarfile
from collections import Counter
from pathlib import Path

from aggregate_data import assignment_coverage, get_member_display, staged_snapshot

ROOT = Path(__file__).resolve().parents[1]
STATES = ("parsed", "partial", "empty_no_tex", "blocked_input", "failed")
COUNTS = ("elements_before_dedup", "elements_after_dedup",
          "bibtex_entries_before_dedup", "bibtex_entries_after_dedup")
METRICS = ("wall_time_s", "export_wall_time_s", "total_wall_time_s", "peak_ram_mb")
DOCUMENTS = {"full/m2_stats.json": "summary", "full/tables/manifest.json": "manifest",
             "full/benchmark/benchmark_receipt.json": "receipt"}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def add_paper(papers, identifier, row):
    check(identifier not in papers, f"Duplicate publication: {identifier}")
    papers[identifier] = row


def version_counts(statuses):
    counts = Counter(statuses.values())
    check(set(counts) <= set(STATES), f"Unknown version status: {counts}")
    return {state: counts[state] for state in STATES}


def collect_archive(archive, run_id):
    docs, papers, versions = {}, {}, {}
    kinds = Counter()
    with gzip.open(archive, "rb") as compressed, tarfile.open(
        fileobj=compressed, mode="r|", bufsize=1024 * 1024
    ) as tar:
        for item in tar:
            if not item.isfile():
                continue
            if item.name in DOCUMENTS:
                key = DOCUMENTS[item.name]
                check(key not in docs, f"Duplicate {item.name}")
                docs[key] = json.load(tar.extractfile(item))
                continue
            match = re.fullmatch(r"full/(\d{4}-\d{5})/stats\.json", item.name)
            if not match:
                continue
            data = json.load(tar.extractfile(item))
            raw_id = match[1]
            pid = raw_id.replace("-", ".")
            check(data["arxiv_id"] == raw_id and data["parser_schema_version"] == 21,
                  f"Paper identity/schema mismatch: {pid}")
            states = data["version_status"]
            counts = version_counts(states)
            check(len(states) == data["versions_seen"] and counts["parsed"] == data["versions_parsed"],
                  f"Version count mismatch: {pid}")
            check(sum(data["kind_counts_before_dedup"].values()) == data["elements_before_dedup"],
                  f"Element breakdown mismatch: {pid}")
            add_paper(papers, pid, dict(arxiv_id=pid, run_id=run_id, versions=len(states),
                      **counts, export_ready=data["export_ready"], **{k: data[k] for k in COUNTS},
                      hierarchy_edges=data["hierarchy_edges"]))
            kinds.update(data["kind_counts_before_dedup"])
            for ver, status in states.items():
                check(str(int(ver)) == ver and int(ver) > 0, f"Invalid version: {pid} v{ver}")
                versions[pid, int(ver)] = status
    check(set(docs) == set(DOCUMENTS.values()), f"Incomplete archive: {archive}")
    return docs, papers, versions, kinds


def validate_export(papers, manifest):
    exclusions = {r["arxiv_id"].replace("-", "."): r["reason"] for r in manifest["excluded"]}
    ready = [row for row in papers.values() if row["export_ready"]]
    check(set(exclusions) == {pid for pid, r in papers.items() if not r["export_ready"]}
          and len(exclusions) == len(manifest["excluded"]) == manifest["publications_excluded"],
          "Excluded publication IDs disagree with the handoff manifest")
    check(len(ready) == manifest["publications_included"] and len(papers) == manifest["publications_expected"],
          "Handoff publication counts disagree")
    fields = {"elements": "elements_after_dedup", "hierarchy": "hierarchy_edges",
              "bibtex": "bibtex_entries_after_dedup"}
    for table, field in fields.items():
        check(sum(r[field] for r in ready) == manifest["rows"][table],
              f"Export-ready {table} counts disagree with the handoff manifest")
    for pid, row in papers.items():
        row["exclusion_reason"] = exclusions.get(pid, "")


def read_run(path, source):
    summary = json.loads(path.read_text(encoding="utf-8"))
    run_id = summary["run_id"]
    print(f"Reading {path.relative_to(source)}", flush=True)
    docs, papers, versions, kinds = collect_archive(path.with_name("full.tar.gz"), run_id)
    manifest, receipt = docs["manifest"], docs["receipt"]
    check(docs["summary"] == summary, f"External and archived summaries disagree: {run_id}")
    check(summary["parser_schema_version"] == 21 and summary["complete_corpus_run"]
          and summary["run_scope"] == "full_corpus" and receipt["complete_corpus_run"]
          and manifest["export_mode"] == "handoff", f"Unexpected run scope: {run_id}")
    check(manifest["run_id"] == receipt["run_id"] == run_id and manifest["snapshot_id"] == path.parents[1].name,
          f"Receipt/manifest source mismatch: {run_id}")
    check(len(papers) == summary["papers_processed"] == summary["papers_requested"]
          and len(versions) == summary["versions_requested"]
          and Counter(versions.values()) == Counter(summary["version_status_counts"]),
          f"Run coverage mismatch: {run_id}")
    for field in COUNTS:
        check(sum(row[field] for row in papers.values()) == summary[field], f"{run_id}: {field}")
    validate_export(papers, manifest)
    check(summary["papers_export_ready"] == manifest["publications_included"], f"Ready count mismatch: {run_id}")
    for field in METRICS:
        check(summary[field] == receipt["metrics"][field], f"Benchmark mismatch: {run_id} {field}")
    member, account = path.relative_to(source).parts[:2]
    disk = summary["output_bytes_breakdown"]
    run = dict(run_id=run_id, member=get_member_display(member), account=account,
               source=path.parent.relative_to(source).as_posix(), schema=summary["parser_schema_version"],
               snapshot_id=manifest["snapshot_id"], code_revision=receipt["git"]["revision"],
               workers=receipt["config"]["workers"], environment=receipt["environment"]["environment_type"],
               colab_cpu_verified=receipt["environment"]["colab_cpu_verified"],
               papers=len(papers), **{k: summary[k] for k in METRICS},
               working_bytes=disk["working_bytes"], tables_directory_bytes=disk["parquet_bytes"],
               parquet_shard_bytes=sum(f["bytes"] for f in manifest["files"]),
               **{f"{k}_rows": manifest["rows"][k] for k in ("elements", "hierarchy", "bibtex")})
    return run, papers, versions, kinds


def write_csv(path, rows):
    rows = iter(rows)
    first = next(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, first.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(first)
        writer.writerows(rows)


def aggregate(source, m1=ROOT / "book/data", target=ROOT / "book/data_m2"):
    with (m1 / "papers_unique.csv").open(encoding="utf-8", newline="") as stream:
        assigned = {}
        for row in csv.DictReader(stream):
            add_paper(assigned, row["arxiv_id"], row)
    coverage = assignment_coverage(assigned)
    check(all(coverage[k] == 0 for k in ("wrong_member_ids_count", "missing_assigned_ids_count",
                                          "unexpected_ids_count")), "M1 differs from the assignment")
    with (m1 / "versions.csv").open(encoding="utf-8", newline="") as stream:
        expected_versions = Counter((r["arxiv_id"], int(r["version"])) for r in csv.DictReader(stream))
    expected_accounts = {(r["member"], r["account"]) for r in assigned.values()}
    runs, papers, versions, kinds = {}, {}, {}, Counter()
    for path in sorted(source.glob("*/*/Milestone2/*/*/full/m2_stats.json")):
        run, batch, states, distribution = read_run(path, source)
        account = (run["member"], run["account"])
        check(account not in runs and run["run_id"] not in {r["run_id"] for r in runs.values()},
              f"Duplicate account or run: {account}")
        runs[account] = run
        for pid, row in batch.items():
            add_paper(papers, pid, row)
            check(pid in assigned and assigned[pid]["member"] == run["member"],
                  f"Wrong assignment: {pid} in {account}")
        versions.update(states)
        kinds.update(distribution)
    check(set(runs) == expected_accounts and set(papers) == set(assigned), "Incomplete assignment coverage")
    check(Counter(versions.keys()) == expected_versions, "M1/M2 publication-version keys differ")
    with staged_snapshot(target) as output:
        output.mkdir()
        write_csv(output / "runs.csv", runs.values())
        write_csv(output / "papers.csv", (papers[pid] for pid in sorted(papers)))
        write_csv(output / "versions.csv", (dict(arxiv_id=pid, version=v, status=versions[pid, v])
                                             for pid, v in sorted(versions)))
        write_csv(output / "node_kinds.csv", (dict(kind=k, occurrences=n) for k, n in kinds.most_common()))
    print(f"Published {len(runs)} runs, {len(papers)} papers and {len(versions)} versions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT.parent / "input")
    aggregate(parser.parse_args().source)
