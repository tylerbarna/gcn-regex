import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from packArchive import pack_archive


BASE_URL = "https://gcn.nasa.gov/circulars/{}.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _archive_folder() -> Path:
    return _repo_root() / "archive"


def _tarballs_folder() -> Path:
    return _repo_root() / "tarballs"


def _load_json_from_url(url: str):
    with urlopen(url, timeout=30) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _latest_circular_id(archive_folder: Path) -> int:
    circular_ids = []
    for path in archive_folder.glob("*.json"):
        try:
            circular_ids.append(int(path.stem))
        except ValueError:
            continue

    if not circular_ids:
        raise FileNotFoundError(f"No circular JSON files found in {archive_folder}")

    return max(circular_ids)


def download_new_circulars(
    archive_folder: Path,
    start_after: int | None = None,
    max_consecutive_failures: int = 3,
):
    archive_folder.mkdir(parents=True, exist_ok=True)

    if start_after is None:
        start_after = _latest_circular_id(archive_folder)

    next_circular_id = start_after + 1
    consecutive_failures = 0
    downloaded = 0

    while consecutive_failures <= max_consecutive_failures:
        circular_url = BASE_URL.format(next_circular_id)
        output_path = archive_folder / f"{next_circular_id}.json"

        if output_path.exists():
            consecutive_failures = 0
            next_circular_id += 1
            continue

        try:
            circular_data = _load_json_from_url(circular_url)
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            consecutive_failures += 1
            print(f"Missing circular {next_circular_id}: {exc}")
            next_circular_id += 1
            continue

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(circular_data, handle, indent=4)

        downloaded += 1
        consecutive_failures = 0
        print(f"Downloaded circular {next_circular_id}")
        next_circular_id += 1

    if downloaded:
        print(f"Downloaded {downloaded} new circulars")
    else:
        print("No new circulars downloaded")

    return downloaded


def sync_circulars(archive_folder, tarballs_folder, max_consecutive_failures: int = 3, max_size_mb: int = 20):
    archive_folder = archive_folder
    tarballs_folder = tarballs_folder 

    downloaded = download_new_circulars(
        archive_folder=archive_folder,
        max_consecutive_failures=max_consecutive_failures,
    )

    if not downloaded:
        print("Archive is up to date.")
        return downloaded

    pack_archive(
        str(archive_folder),
        str(tarballs_folder),
        max_size_mb=max_size_mb,
        overwrite=True,
    )

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Download new GCN circular JSON files and repack the archive")
    parser.add_argument(
        "--max_consecutive_failures",
        type=int,
        default=3,
        help="Stop after this many consecutive missing JSON files",
    )
    parser.add_argument(
        "--max_size_mb",
        type=int,
        default=20,
        help="Maximum tarball size passed through to packArchive.py",
    )
    parser.add_argument(
        "--archive_folder",
        type=str,
        default=str(_archive_folder()),
        help="Path to the archive folder (default: ./archive)",
    )
    parser.add_argument(
        "--tarballs_folder",
        type=str,
        default=str(_tarballs_folder()),
        help="Path to the tarballs folder (default: ./tarballs)",
    )

    args = parser.parse_args()
    sync_circulars(
        archive_folder=Path(args.archive_folder),
        tarballs_folder=Path(args.tarballs_folder),
        max_consecutive_failures=args.max_consecutive_failures,
        max_size_mb=args.max_size_mb,
    )


if __name__ == "__main__":
    main()