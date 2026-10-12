"""File Processing Workload — generates text and performs analysis.

Performs word count, line count, character frequency, and text statistics
inside a Docker container. Uses only Python stdlib.
"""

import argparse
import sys
import time
import json
import random
import string
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description='File Processing Workload')
    parser.add_argument('--size-kb', type=int, default=100, help='Size of text to generate in KB')
    args = parser.parse_args()

    start = time.time()
    print(f'[File Processing] Size: {args.size_kb} KB')

    # Generate text content
    text = _generate_text(args.size_kb)
    print(f'Generated {len(text)} bytes of text')

    # Process text
    results = _process_text(text)
    elapsed = time.time() - start

    output = {
        'input_size_kb': args.size_kb,
        'actual_size_bytes': len(text),
        'analysis': results,
        'duration_seconds': round(elapsed, 3),
        'status': 'success',
    }
    print(json.dumps(output, indent=2))
    return 0


def _generate_text(size_kb):
    """Generate realistic-looking text of the specified size."""
    random.seed(42)
    words = [
        'the', 'quick', 'brown', 'fox', 'jumps', 'over', 'lazy', 'dog',
        'cloud', 'computing', 'scheduler', 'resource', 'allocation', 'node',
        'container', 'docker', 'processing', 'analysis', 'data', 'system',
        'network', 'distributed', 'parallel', 'concurrent', 'algorithm',
        'optimization', 'throughput', 'latency', 'bandwidth', 'memory',
        'storage', 'virtual', 'machine', 'instance', 'deployment', 'service',
        'microservice', 'kubernetes', 'orchestration', 'scaling', 'monitoring',
    ]

    target_bytes = size_kb * 1024
    lines = []
    current_size = 0

    while current_size < target_bytes:
        line_words = random.randint(5, 15)
        line = ' '.join(random.choice(words) for _ in range(line_words))
        # Capitalize first word, add period
        line = line[0].upper() + line[1:] + '.'
        lines.append(line)
        current_size += len(line) + 1  # +1 for newline

    return '\n'.join(lines)


def _process_text(text):
    """Analyze text and return statistics."""
    lines = text.split('\n')
    words = text.split()
    chars = list(text)

    # Character frequency (top 10)
    char_freq = Counter(c.lower() for c in chars if c.isalpha())
    top_chars = char_freq.most_common(10)

    # Word frequency (top 15)
    word_freq = Counter(w.lower().strip('.,!?') for w in words)
    top_words = word_freq.most_common(15)

    # Sentence length distribution
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    return {
        'total_lines': len(lines),
        'total_words': len(words),
        'total_characters': len(chars),
        'unique_words': len(set(w.lower().strip('.,!?') for w in words)),
        'avg_word_length': round(sum(len(w) for w in words) / max(len(words), 1), 2),
        'avg_sentence_length': round(avg_sentence_len, 2),
        'total_sentences': len(sentences),
        'top_characters': [{'char': c, 'count': n} for c, n in top_chars],
        'top_words': [{'word': w, 'count': n} for w, n in top_words],
    }


if __name__ == '__main__':
    sys.exit(main())
