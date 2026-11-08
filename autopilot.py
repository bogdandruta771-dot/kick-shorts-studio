"""
Standalone CLI Runner for OmniStudio 24/7 Autopilot.
Allows running 1-click end-to-end shorts generation or starting a continuous background daemon.
Usage:
  python autopilot.py --once                   # Generate 1 short right now (A to Z)
  python autopilot.py --topic "Custom Topic"   # Generate 1 short on specific topic
  python autopilot.py --daemon --interval 180  # Run 24/7 in background every 3 hours
  python autopilot.py --auto-upload            # Automatically publish to YouTube
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.autopilot import autopilot


def main():
    parser = argparse.ArgumentParser(description="OmniStudio A-to-Z Autopilot Automation")
    parser.add_argument("--once", action="store_true", help="Generate a single short from A to Z right now")
    parser.add_argument("--topic", type=str, default=None, help="Custom topic for the short")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background on a schedule")
    parser.add_argument("--interval", type=int, default=180, help="Interval in minutes between runs (default: 180)")
    parser.add_argument("--auto-upload", action="store_true", help="Automatically upload finished video to YouTube")
    parser.add_argument("--voice", type=str, default="en-US-ChristopherNeural", help="Voice ID (Edge-TTS or ElevenLabs)")

    args = parser.parse_args()

    print("=" * 65)
    print("  🚀 OMNISTUDIO 24/7 AUTOPILOT FACTORY (A TO Z)")
    print("=" * 65)

    if args.daemon:
        print(f"[*] Starting 24/7 background factory (every {args.interval} minutes)...")
        print(f"[*] Auto-upload to YouTube: {args.auto_upload}")
        print("Press Ctrl+C to terminate.")
        autopilot.start(
            interval_minutes=args.interval,
            auto_upload=args.auto_upload,
            voice_id=args.voice
        )
        try:
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopping autopilot...")
            autopilot.stop()
            print("Stopped cleanly.")
    else:
        # Single cycle run
        print("[*] Running single end-to-end A-to-Z production cycle...")
        def _prog(pct, msg):
            print(f"[{int(pct * 100)}%] {msg}")

        res = autopilot.run_single_faceless_cycle(
            topic=args.topic,
            auto_upload=args.auto_upload,
            progress_cb=_prog
        )

        print("=" * 65)
        print("  ✅ AUTOPILOT PRODUCTION FINISHED!")
        print(f"  🎬 Video:       {res['filename']}")
        print(f"  ⏱️ Duration:    {res['duration']}s")
        print(f"  🏷️ Title:       {res['title']}")
        print(f"  📤 Uploaded:    {res['uploaded']}")
        print("=" * 65)


if __name__ == "__main__":
    main()
