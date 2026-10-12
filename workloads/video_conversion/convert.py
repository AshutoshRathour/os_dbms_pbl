"""Video Conversion Workload — compute-intensive frame generation and encoding simulation.

Generates synthetic video frames and performs compression/encoding operations
inside a Docker container. Uses only Python stdlib.
"""

import argparse
import sys
import time
import json
import random
import hashlib
import struct
import zlib


def main():
    parser = argparse.ArgumentParser(description='Video Conversion Workload')
    parser.add_argument('--duration', type=int, default=5, help='Video duration in seconds')
    args = parser.parse_args()

    start = time.time()
    fps = 24
    total_frames = args.duration * fps
    width, height = 320, 240

    print(f'[Video Conversion] Duration: {args.duration}s, FPS: {fps}, '
          f'Resolution: {width}x{height}, Frames: {total_frames}')

    # Generate and "encode" frames
    frame_sizes = []
    frame_hashes = []
    total_raw_bytes = 0
    total_compressed_bytes = 0

    for i in range(total_frames):
        # Generate a raw frame (RGB data)
        frame = _generate_frame(width, height, i, total_frames)
        raw_size = len(frame)
        total_raw_bytes += raw_size

        # Simulate encoding via compression
        compressed = zlib.compress(frame, level=6)
        compressed_size = len(compressed)
        total_compressed_bytes += compressed_size

        frame_hash = hashlib.md5(frame).hexdigest()[:8]
        frame_sizes.append(compressed_size)
        frame_hashes.append(frame_hash)

        if (i + 1) % fps == 0:
            sec = (i + 1) // fps
            print(f'  Encoded second {sec}/{args.duration} '
                  f'({i+1}/{total_frames} frames)')

    elapsed = time.time() - start
    compression_ratio = total_raw_bytes / max(total_compressed_bytes, 1)

    output = {
        'duration_seconds': args.duration,
        'fps': fps,
        'resolution': f'{width}x{height}',
        'total_frames': total_frames,
        'total_raw_bytes': total_raw_bytes,
        'total_compressed_bytes': total_compressed_bytes,
        'compression_ratio': round(compression_ratio, 2),
        'avg_frame_size': round(sum(frame_sizes) / len(frame_sizes), 0),
        'processing_time_seconds': round(elapsed, 3),
        'encoding_fps': round(total_frames / max(elapsed, 0.001), 1),
        'status': 'success',
    }
    print(json.dumps(output, indent=2))
    return 0


def _generate_frame(width, height, frame_num, total_frames):
    """Generate a synthetic frame with animated gradient pattern."""
    random.seed(frame_num)
    phase = frame_num / total_frames
    data = bytearray()

    for y in range(height):
        for x in range(width):
            r = int(127 + 127 * ((x / width + phase) % 1.0))
            g = int(127 + 127 * ((y / height + phase * 0.7) % 1.0))
            b = int(127 + 127 * (((x + y) / (width + height) + phase * 1.3) % 1.0))
            data.extend([r & 0xFF, g & 0xFF, b & 0xFF])

    return bytes(data)


if __name__ == '__main__':
    sys.exit(main())
