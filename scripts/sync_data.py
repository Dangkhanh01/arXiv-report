#!/usr/bin/env python3
"""Compatibility entry point for receipt-verified, transactional aggregation.

Use the same member/account/Milestone1 input tree and arguments as aggregate_data.py.
Single-archive extraction and partial pre-aggregated copying are intentionally no
longer supported: they can mix snapshots or bypass receipt/schema checks.
"""
from aggregate_data import main

if __name__ == "__main__":
    main()
