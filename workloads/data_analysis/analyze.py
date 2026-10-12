"""Data Analysis Workload — generates and analyzes a dataset.

Performs statistical analysis on generated data inside a Docker container.
Uses only Python stdlib for a minimal image size.
"""

import argparse
import sys
import time
import json
import random
import math
import statistics


def main():
    parser = argparse.ArgumentParser(description='Data Analysis Workload')
    parser.add_argument('--rows', type=int, default=1000, help='Number of data rows to generate and analyze')
    args = parser.parse_args()

    start = time.time()
    print(f'[Data Analysis] Rows: {args.rows}')

    # Generate dataset
    random.seed(42)
    data = _generate_dataset(args.rows)
    print(f'Generated dataset with {args.rows} rows, 5 columns')

    # Perform analysis
    results = _analyze(data)
    elapsed = time.time() - start

    output = {
        'rows_analyzed': args.rows,
        'columns': list(results.keys()),
        'statistics': results,
        'duration_seconds': round(elapsed, 3),
        'status': 'success',
    }
    print(json.dumps(output, indent=2))
    return 0


def _generate_dataset(rows):
    """Generate a synthetic dataset with 5 numeric columns."""
    columns = {
        'revenue': [random.gauss(1000, 200) for _ in range(rows)],
        'cost': [random.gauss(600, 150) for _ in range(rows)],
        'units_sold': [max(0, int(random.gauss(50, 20))) for _ in range(rows)],
        'satisfaction': [min(10, max(0, random.gauss(7, 1.5))) for _ in range(rows)],
        'response_time_ms': [max(1, random.expovariate(1/200)) for _ in range(rows)],
    }
    return columns


def _analyze(data):
    """Compute statistics for each column."""
    results = {}
    for col_name, values in data.items():
        sorted_vals = sorted(values)
        n = len(values)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]

        results[col_name] = {
            'count': n,
            'mean': round(statistics.mean(values), 4),
            'median': round(statistics.median(values), 4),
            'stdev': round(statistics.stdev(values), 4),
            'min': round(min(values), 4),
            'max': round(max(values), 4),
            'q1': round(q1, 4),
            'q3': round(q3, 4),
            'iqr': round(q3 - q1, 4),
        }

        # Compute correlation with the first column (revenue)
        if col_name != 'revenue':
            revenue = data['revenue']
            corr = _pearson_correlation(revenue, values)
            results[col_name]['correlation_with_revenue'] = round(corr, 4)

    return results


def _pearson_correlation(x, y):
    """Compute Pearson correlation coefficient."""
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    if den_x * den_y == 0:
        return 0
    return num / (den_x * den_y)


if __name__ == '__main__':
    sys.exit(main())
