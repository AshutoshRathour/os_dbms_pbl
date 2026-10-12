"""Image Processing Workload — generates a test image and applies filters.

Uses Pillow to create and manipulate images inside a Docker container.
This is a real workload, not a simulation.
"""

import argparse
import sys
import time
import json
from PIL import Image, ImageFilter, ImageOps
import io


def main():
    parser = argparse.ArgumentParser(description='Image Processing Workload')
    parser.add_argument('--operation', choices=['blur', 'sharpen', 'grayscale', 'resize', 'edge_detect'],
                        default='blur', help='Image operation to perform')
    parser.add_argument('--size', type=int, default=512, help='Image size (width=height)')
    args = parser.parse_args()

    start = time.time()
    print(f'[Image Processing] Operation: {args.operation}, Size: {args.size}x{args.size}')

    # Generate a test image with a gradient pattern
    img = _generate_test_image(args.size)
    print(f'Generated test image: {args.size}x{args.size} pixels')

    # Apply the requested operation
    result = _apply_operation(img, args.operation, args.size)
    elapsed = time.time() - start

    # Output results as JSON for structured parsing
    output = {
        'operation': args.operation,
        'input_size': f'{args.size}x{args.size}',
        'output_size': f'{result.size[0]}x{result.size[1]}',
        'mode': result.mode,
        'duration_seconds': round(elapsed, 3),
        'status': 'success',
    }
    print(json.dumps(output, indent=2))
    return 0


def _generate_test_image(size):
    """Create a gradient test image with some complexity."""
    img = Image.new('RGB', (size, size))
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            r = int(255 * x / size)
            g = int(255 * y / size)
            b = int(255 * (x + y) / (2 * size))
            pixels[x, y] = (r, g, b)
    return img


def _apply_operation(img, operation, size):
    """Apply the requested image operation."""
    if operation == 'blur':
        # Multi-pass Gaussian blur for heavier computation
        for _ in range(3):
            img = img.filter(ImageFilter.GaussianBlur(radius=5))
        print('Applied 3-pass Gaussian blur')

    elif operation == 'sharpen':
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.DETAIL)
        print('Applied sharpen + detail enhancement')

    elif operation == 'grayscale':
        img = ImageOps.grayscale(img)
        print('Converted to grayscale')

    elif operation == 'resize':
        new_size = size * 2
        img = img.resize((new_size, new_size), Image.LANCZOS)
        img = img.resize((size // 2, size // 2), Image.LANCZOS)
        print(f'Resized: upscale to {new_size}x{new_size}, then downscale to {size//2}x{size//2}')

    elif operation == 'edge_detect':
        img = img.filter(ImageFilter.FIND_EDGES)
        img = img.filter(ImageFilter.CONTOUR)
        print('Applied edge detection + contour')

    return img


if __name__ == '__main__':
    sys.exit(main())
