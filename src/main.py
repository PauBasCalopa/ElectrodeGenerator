#!/usr/bin/env python3
"""
Electrode Profile Generator — main entry point.

Usage:
    python main.py              Launch GUI (default)
    python main.py --cli        Interactive CLI mode
    python main.py --cli --profile chang
"""

import sys
import argparse
from datetime import datetime
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


def run_cli(args):
    """Run the interactive CLI workflow."""
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

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # PNG
    png_path = f"{profile.name}_{stamp}.png"
    plt.figure(figsize=(12, 8))
    plt.plot(x, y, 'b-', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title(f'{profile.name} Profile')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {png_path}")

    # DXF
    dxf_path = f"{profile.name}_{stamp}.dxf"
    exporter = DXFExporter()
    exporter.create_new_document()
    exporter.add_spline(profile.to_polyline_points(config), 'PROFILE')
    exporter.save_to_file(dxf_path)
    print(f"DXF saved: {dxf_path}")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Electrode Profile Generator")
    parser.add_argument('--cli', action='store_true',
                        help='Run in interactive CLI mode instead of GUI')
    parser.add_argument('--profile', choices=[k.lower() for k in PROFILES],
                        default='rogowski', help='Profile type for CLI mode (default: rogowski)')
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        from gui import ProfileGeneratorGUI
        ProfileGeneratorGUI().run()


if __name__ == "__main__":
    main()