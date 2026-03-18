#!/usr/bin/env python3
"""
Profile Generator — CLI mode.

Usage:
    python main.py
    python main.py --profile chang
"""

import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from profiles import PROFILES, ProfileBase
from dxf_exporter import DXFExporter


def get_user_input(profile: ProfileBase) -> dict:
    """Get parameter values from user input based on the profile's parameter list."""
    print(f"\n=== {profile.name} Profile ===")
    config = {}
    for p in profile.parameters:
        while True:
            try:
                raw = input(f"  {p['label']} [default: {p['default']}]: ") or str(p['default'])
                value = p['type'](raw)
                config[p['name']] = value
                break
            except ValueError:
                print(f"  Please enter a valid {p['type'].__name__}.")
    return config


def main():
    parser = argparse.ArgumentParser(description="Generate electrode profile geometry")
    parser.add_argument('--profile', choices=[k.lower() for k in PROFILES],
                        default='rogowski', help='Profile type (default: rogowski)')
    args = parser.parse_args()

    profile = PROFILES[args.profile.capitalize()]

    print("=" * 60)
    print(f"Profile Generator — {profile.name}")
    print("=" * 60)

    config = get_user_input(profile)

    # All profiles use s (electrode gap)
    while True:
        try:
            config['s'] = float(input("  s (electrode gap) [default: 2.0]: ") or "2.0")
            break
        except ValueError:
            print("  Please enter a valid number.")

    x, y = profile.generate_points(config)

    bbox = profile.get_bounding_box(config)
    print(f"\nBounding box:")
    print(f"  X: [{bbox['min_x']:.4f}, {bbox['max_x']:.4f}]")
    print(f"  Y: [{bbox['min_y']:.4f}, {bbox['max_y']:.4f}]")

    # PNG
    plt.figure(figsize=(12, 8))
    plt.plot(x, y, 'b-', linewidth=2, label=f'{profile.name} Profile')
    plt.grid(True, alpha=0.3)
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title(f'{profile.name} Profile')
    plt.legend()
    plt.savefig('profile_plot.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Plot saved: profile_plot.png")

    # DXF
    exporter = DXFExporter()
    exporter.create_new_document()
    exporter.add_polyline(profile.to_polyline_points(config), 'PROFILE')
    exporter.save_to_file('profile_output.dxf')

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()