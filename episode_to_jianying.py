import argparse
import json
from pathlib import Path


def convert_episode(
    episode_path: Path,
    output_path: Path,
    draft_name: str,
    draft_root: str | None = None,
) -> Path:
    episode_path = episode_path.resolve()
    output_path = output_path.resolve()
    episode = json.loads(episode_path.read_text(encoding="utf-8-sig"))
    shots = episode.get("shots") or []
    if not shots:
        raise ValueError("episode.json 至少需要一个 shot")

    image_ranges = []
    images = []
    cursor = 0.0
    for shot in shots:
        duration = float(shot["duration"])
        if duration <= 0:
            raise ValueError("shot duration 必须大于 0")
        images.append(str(shot["image"]))
        image_ranges.append({"start": round(cursor, 3), "duration": round(duration, 3)})
        cursor += duration

    manifest = {
        "draft_name": draft_name,
        "width": int(episode.get("width", 1080)),
        "height": int(episode.get("height", 1920)),
        "fps": int(episode.get("fps", 30)),
        "images": images,
        "image_ranges": image_ranges,
        "voice": episode.get("voice", ""),
        "bgm": episode.get("bgm", ""),
        "voice_volume": float(episode.get("voice_volume", 1.0)),
        "bgm_volume": float(episode.get("bgm_volume", 0.10)),
        "ken_burns": bool(episode.get("ken_burns", True)),
        "ken_burns_scale": float(episode.get("ken_burns_scale", 1.045)),
        "captions": episode.get("captions") or [],
    }
    if draft_root:
        manifest["draft_root"] = draft_root

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert episode.json to a Jianying draft manifest")
    parser.add_argument("--episode", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--draft-name", required=True)
    parser.add_argument("--draft-root")
    args = parser.parse_args()
    result = convert_episode(args.episode, args.output, args.draft_name, args.draft_root)
    print(result)


if __name__ == "__main__":
    main()
