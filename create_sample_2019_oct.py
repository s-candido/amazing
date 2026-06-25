#!/usr/bin/env python3
"""Create 10% sample of a CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create 10% sample of a CSV file"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to CSV file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "dags" / "src" / "data_folder",
        help="Output folder for sampled CSV files",
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

    if not args.input.is_file():
        raise ValueError(f"Input path is not a file: {args.input}")

    if args.input.suffix.lower() != ".csv":
        raise ValueError(f"Input file must be a CSV file: {args.input}")

    # Create output folder if it doesn't exist
    args.output.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Reading {args.input.name} in chunks...")
        
        # Read CSV in chunks to avoid loading the entire file in memory
        chunks = []
        total_rows = 0
        
        for chunk in pd.read_csv(args.input, chunksize=10000):
            total_rows += len(chunk)
            # Sample 10% from each chunk
            chunk_sample = chunk.sample(frac=0.10, random_state=args.seed + total_rows)
            chunks.append(chunk_sample)
        
        df_sample = pd.concat(chunks, ignore_index=True)
        print(f"Original size: {total_rows} rows")
        
        # Create output filename with -10pct suffix
        output_file = args.output / f"{args.input.stem}-10pct.csv"
        df_sample.to_csv(output_file, index=False)
        
        print(f"Created sample: {len(df_sample)} rows -> {output_file}")
    except Exception as e:
        print(f"Error processing {args.input.name}: {e}")
        raise


if __name__ == "__main__":
    main()
