#!/usr/bin/env python3
"""Create a 10% sample of the 2019-Oct.csv dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a 10% sample of 2019-Oct.csv"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data_folder" / "2019-Oct.csv",
        help="Path to 2019-Oct.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "data_folder"
        / "2019-Oct-10pct.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    df = pd.read_csv(args.input)
    sample = df.sample(frac=0.10, random_state=args.seed)
    sample.to_csv(args.output, index=False)

    print(f"Wrote {len(sample)} rows to {args.output}")


if __name__ == "__main__":
    main()
