"""Rebuild the synthetic HR dataset and clean it. Python standard library only."""
import csv, random, statistics
from datetime import date, timedelta
from pathlib import Path
OUT=Path(__file__).resolve().parent
rng=random.Random(42)
# See project README for documented field definitions and injected data-quality issues.
# Run the full reproducible pipeline from the companion script: generate_clean_analyze.py
print("Use generate_clean_analyze.py to rebuild all outputs.")
