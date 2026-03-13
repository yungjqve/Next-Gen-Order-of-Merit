from __future__ import annotations

import argparse
import os
import sys

from .fetcher import fetch_ranking_payload
from .parser import parse_players
from .qualifiers import pick_qualifiers
from .report import build_html

MAIN_URL_DEFAULT = "https://tv.dartconnect.com/rankings/pdc-next-gen-2026"
YOUTH_URL_DEFAULT = "https://tv.dartconnect.com/rankings/pdc-next-gen-youth-2026"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Scrape DartConnect rankings and generate an HTML report")
    ap.add_argument("--main", default=MAIN_URL_DEFAULT, help="Main Order of Merit URL")
    ap.add_argument("--youth", default=YOUTH_URL_DEFAULT, help="Youth Order of Merit URL")
    ap.add_argument("--out", default="rankings.html", help="Output HTML file")
    ap.add_argument("--view", choices=["main", "youth", "interesting"], default="main", help="Which table view to render")
    ap.add_argument("--mobile", action="store_true", help="Render compact mobile page variant")
    ap.add_argument("--main-qual", type=int, default=16, help="Number of main qualifiers")
    ap.add_argument("--youth-qual", type=int, default=4, help="Number of youth qualifiers")
    ap.add_argument("--generate-all", action="store_true", help="Generate all 6 HTML variants (main/youth/interesting x desktop/mobile)")
    ap.add_argument("--out-dir", default="/var/www/next.jqve.dev", help="Output directory for --generate-all")
    ap.add_argument(
        "--cookie",
        default=os.environ.get("DARTCONNECT_COOKIE", ""),
        help="Cookie header string, e.g. 'a=b; c=d' (or set DARTCONNECT_COOKIE env var)",
    )
    return ap.parse_args()


def _fetch_and_prepare(args: argparse.Namespace):
    """Fetch API data and compute qualifiers (shared by single and generate-all modes)."""
    cookie_header = args.cookie.strip() or None

    main_payload = fetch_ranking_payload(args.main, cookie_header=cookie_header)
    youth_payload = fetch_ranking_payload(args.youth, cookie_header=cookie_header)

    main_players = parse_players(main_payload)
    youth_players = parse_players(youth_payload)

    if not main_players:
        raise RuntimeError("Could not parse Main players from rankings API payload.")
    if not youth_players:
        raise RuntimeError("Could not parse Youth players from rankings API payload.")

    main_q, youth_q, all_q = pick_qualifiers(main_players, youth_players, args.main_qual, args.youth_qual)
    return main_players, youth_players, main_q, youth_q, all_q


def _write_html(path: str, html: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def run() -> int:
    args = parse_args()

    if args.generate_all:
        return _run_generate_all(args)

    main_players, youth_players, main_q, youth_q, all_q = _fetch_and_prepare(args)
    out_html = build_html(
        main=main_players,
        youth=youth_players,
        main_q=main_q,
        youth_q=youth_q,
        all_q=all_q,
        main_url=args.main,
        youth_url=args.youth,
        view=args.view,
        mobile=args.mobile,
    )

    _write_html(args.out, out_html)
    print(f"Wrote {args.out} (main rows: {len(main_players)}, youth rows: {len(youth_players)})")
    return 0


def _run_generate_all(args: argparse.Namespace) -> int:
    """Generate all 6 HTML variants from a single pair of API calls."""
    import copy

    main_players, youth_players, main_q, youth_q, all_q = _fetch_and_prepare(args)
    out_dir = args.out_dir.rstrip("/")

    variants = [
        ("main",        False, f"{out_dir}/index.html"),
        ("main",        True,  f"{out_dir}/mobile/index.html"),
        ("youth",       False, f"{out_dir}/youth/index.html"),
        ("youth",       True,  f"{out_dir}/youth/mobile/index.html"),
        ("interesting", False, f"{out_dir}/interesting/index.html"),
        ("interesting", True,  f"{out_dir}/interesting/mobile/index.html"),
    ]

    for view, mobile, path in variants:
        # Deep-copy players so qualifier flags from build_html don't bleed between views
        html = build_html(
            main=copy.deepcopy(main_players),
            youth=copy.deepcopy(youth_players),
            main_q=main_q,
            youth_q=youth_q,
            all_q=all_q,
            main_url=args.main,
            youth_url=args.youth,
            view=view,
            mobile=mobile,
        )
        _write_html(path, html)
        print(f"Wrote {path}")

    print(f"Generated all 6 variants (main rows: {len(main_players)}, youth rows: {len(youth_players)})")
    return 0


def main() -> int:
    try:
        return run()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
