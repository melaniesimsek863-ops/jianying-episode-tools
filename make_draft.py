import argparse
import json
import math
import os
import shutil
import sys
import time
import uuid
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pyJianYingDraft as jy


DEFAULT_DRAFT_ROOT = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft"
)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def sec(value: float) -> int:
    return int(round(value * jy.SEC))


def jy_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_path(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def collect_images(base: Path, manifest: dict) -> list[Path]:
    if "images" in manifest:
        images = [resolve_path(base, item) for item in manifest["images"]]
        return [p for p in images if p is not None]
    image_dir = resolve_path(base, manifest.get("image_dir", "images"))
    if image_dir is None or not image_dir.exists():
        raise FileNotFoundError(f"图片目录不存在: {image_dir}")
    return sorted([p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS])


def normalize_captions(manifest: dict, total_duration: float, image_count: int) -> list[dict]:
    captions = manifest.get("captions") or []
    if captions:
        return captions
    image_duration = float(manifest.get("image_duration", 2.5))
    generated = []
    for index in range(image_count):
        generated.append(
            {
                "text": f"自动字幕测试 {index + 1}",
                "start": round(index * image_duration, 3),
                "duration": image_duration,
            }
        )
    return generated


def allocate_image_ranges(manifest: dict, captions: list[dict], image_count: int) -> list[tuple[int, int]]:
    if image_count == 0:
        raise ValueError("至少需要 1 张图片")

    explicit = manifest.get("image_ranges")
    if explicit:
        return [(sec(item["start"]), sec(item["duration"])) for item in explicit]

    image_duration = float(manifest.get("image_duration", 2.5))
    if captions:
        total = max(float(c["start"]) + float(c["duration"]) for c in captions)
    else:
        total = image_count * image_duration

    ranges = []
    start = 0.0
    for index in range(image_count):
        if index == image_count - 1:
            duration = max(image_duration, total - start)
        else:
            duration = image_duration
        ranges.append((sec(start), sec(duration)))
        start += duration
    return ranges


def build_video_segment(
    material: jy.VideoMaterial,
    start_us: int,
    duration_us: int,
    ken_burns: bool,
    ken_scale: float,
    canvas_blur: float = 0.32,
) -> jy.VideoSegment:
    segment = jy.VideoSegment(material, jy.Timerange(start_us, duration_us))
    segment.add_background_filling("blur", blur=canvas_blur)
    if ken_burns:
        segment.add_keyframe(jy.KeyframeProperty.uniform_scale, 0, 1.0)
        segment.add_keyframe(jy.KeyframeProperty.uniform_scale, max(duration_us - 1, 0), ken_scale)
    return segment


def build_caption_segment(
    text: str,
    start_us: int,
    duration_us: int,
    transform_y: float = -0.62,
    font_size: float = 7.0,
) -> jy.TextSegment:
    return jy.TextSegment(
        text,
        jy.Timerange(start_us, duration_us),
        style=jy.TextStyle(size=font_size, bold=True, align=1, auto_wrapping=True, max_line_width=0.82),
        clip_settings=jy.ClipSettings(transform_y=transform_y),
        border=jy.TextBorder(alpha=1.0, color=(0.0, 0.0, 0.0), width=42.0),
    )


def make_demo_assets(project_dir: Path) -> None:
    asset_dir = project_dir / "assets"
    image_dir = project_dir / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    for idx, color in enumerate([(40, 54, 72), (84, 65, 50), (48, 76, 64)], start=1):
        img = Image.new("RGB", (1920, 1080), color)
        draw = ImageDraw.Draw(img)
        try:
            big = ImageFont.truetype("arial.ttf", 88)
            small = ImageFont.truetype("arial.ttf", 44)
        except Exception:
            big = ImageFont.load_default()
            small = ImageFont.load_default()
        draw.rectangle((80, 80, 1840, 1000), outline=(235, 235, 225), width=6)
        draw.text((130, 410), f"LIFE COPY DEMO {idx:02d}", fill=(255, 255, 255), font=big)
        draw.text((135, 540), "16:9 still image in a 9:16 Jianying draft", fill=(225, 232, 232), font=small)
        img.save(image_dir / f"{idx:03d}.png")

    wav_path = asset_dir / "voice.wav"
    sample_rate = 44100
    duration = 9.0
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(int(sample_rate * duration)):
            tone = 350 if i < sample_rate * 3 else 440 if i < sample_rate * 6 else 520
            value = int(9000 * math.sin(2 * math.pi * tone * i / sample_rate))
            frames += value.to_bytes(2, "little", signed=True)
        wf.writeframes(frames)


def write_demo_manifest(path: Path) -> None:
    manifest = {
        "draft_name": "codex_pipeline_demo",
        "draft_root": str(DEFAULT_DRAFT_ROOT),
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "image_dir": "images",
        "voice": "assets/voice.wav",
        "bgm": "",
        "image_duration": 3.0,
        "voice_volume": 0.35,
        "bgm_volume": 0.12,
        "ken_burns": True,
        "ken_burns_scale": 1.06,
        "captions": [
            {"text": "这是自动草稿流水线第一句。", "start": 0.0, "duration": 3.0},
            {"text": "图片、字幕、口播已经自动摆进时间线。", "start": 3.0, "duration": 3.0},
            {"text": "后面可以换成你的人生副本素材。", "start": 6.0, "duration": 3.0},
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def register_root_meta(
    draft_root: Path,
    draft_name: str,
    draft_path: Path,
    cover_path: Path,
    duration_us: int,
) -> Path | None:
    root_meta_path = draft_root / "root_meta_info.json"
    if not root_meta_path.exists():
        # Jianying 6 can discover drafts by scanning child directories and may
        # no longer create the legacy root index used by older installations.
        return None

    backup = draft_path / f"root_meta_info.before_{draft_name}.{int(time.time())}.json"
    shutil.copy2(root_meta_path, backup)

    data = read_json(root_meta_path)
    store = data.setdefault("all_draft_store", [])
    store[:] = [item for item in store if item.get("draft_name") != draft_name]
    now = int(time.time() * 1_000_000)
    draft_path_jy = jy_path(draft_path)
    store.insert(
        0,
        {
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": jy_path(cover_path),
            "draft_fold_path": draft_path_jy,
            "draft_id": str(uuid.uuid4()).upper(),
            "draft_is_ai_shorts": False,
            "draft_is_invisible": False,
            "draft_json_file": draft_path_jy + "\\draft_content.json",
            "draft_name": draft_name,
            "draft_new_version": "",
            "draft_root_path": jy_path(draft_root),
            "draft_timeline_materials_size": 0,
            "draft_type": "",
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_modified": 0,
            "tm_draft_create": now,
            "tm_draft_modified": now,
            "tm_draft_removed": 0,
            "tm_duration": duration_us,
        },
    )
    data["draft_ids"] = len(store)
    data["root_path"] = jy_path(draft_root)
    root_meta_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return backup


def build_draft(manifest_path: Path) -> Path:
    base = manifest_path.parent.resolve()
    manifest = read_json(manifest_path)
    draft_root = resolve_path(base, manifest.get("draft_root")) or DEFAULT_DRAFT_ROOT
    draft_name = manifest.get("draft_name") or f"codex_auto_{int(time.time())}"
    width = int(manifest.get("width", 1080))
    height = int(manifest.get("height", 1920))
    fps = int(manifest.get("fps", 30))

    images = collect_images(base, manifest)
    captions = normalize_captions(manifest, 0, len(images))
    image_ranges = allocate_image_ranges(manifest, captions, len(images))
    total_duration = max(
        [start + duration for start, duration in image_ranges]
        + [sec(float(c["start"]) + float(c["duration"])) for c in captions]
    )

    folder = jy.DraftFolder(str(draft_root))
    script = folder.create_draft(draft_name, width=width, height=height, fps=fps, allow_replace=True)
    video_track = script.append_track(jy.TrackSpec(jy.TrackType.video, name="images"))
    text_track = script.append_track(jy.TrackSpec(jy.TrackType.text, name="subtitles"))

    ken_burns = bool(manifest.get("ken_burns", True))
    ken_scale = float(manifest.get("ken_burns_scale", 1.06))
    canvas_blur = float(manifest.get("canvas_blur", 0.32))
    for index, image_path in enumerate(images):
        start_us, duration_us = image_ranges[min(index, len(image_ranges) - 1)]
        material = jy.VideoMaterial(str(image_path), material_name=image_path.name)
        segment = build_video_segment(material, start_us, duration_us, ken_burns, ken_scale, canvas_blur)
        script.add_material(material)
        script.add_segment(segment, video_track)

    voice = resolve_path(base, manifest.get("voice"))
    if voice and voice.exists():
        audio_track = script.append_track(jy.TrackSpec(jy.TrackType.audio, name="voice"))
        mat = jy.AudioMaterial(str(voice), material_name=voice.name)
        script.add_material(mat)
        script.add_segment(
            jy.AudioSegment(mat, jy.Timerange(0, total_duration), volume=float(manifest.get("voice_volume", 1.0))),
            audio_track,
        )

    bgm = resolve_path(base, manifest.get("bgm"))
    if bgm and bgm.exists():
        bgm_track = script.append_track(jy.TrackSpec(jy.TrackType.audio, name="bgm"))
        mat = jy.AudioMaterial(str(bgm), material_name=bgm.name)
        script.add_material(mat)
        bgm_segment = jy.AudioSegment(mat, jy.Timerange(0, total_duration), volume=float(manifest.get("bgm_volume", 0.12)))
        bgm_segment.add_keyframe(0, 0.0)
        bgm_segment.add_keyframe(sec(1.0), float(manifest.get("bgm_volume", 0.12)))
        bgm_segment.add_keyframe(max(total_duration - sec(1.0), 0), float(manifest.get("bgm_volume", 0.12)))
        bgm_segment.add_keyframe(total_duration, 0.0)
        script.add_segment(bgm_segment, bgm_track)

    for caption in captions:
        text = str(caption["text"]).strip()
        if not text:
            continue
        script.add_segment(
            build_caption_segment(
                text,
                sec(float(caption["start"])),
                sec(float(caption["duration"])),
                transform_y=float(manifest.get("subtitle_y", -0.62)),
                font_size=float(manifest.get("subtitle_size", 7.0)),
            ),
            text_track,
        )

    script.save()
    draft_path = draft_root / draft_name
    cover_path = draft_path / "draft_cover.jpg"
    Image.open(images[0]).save(cover_path)
    backup = register_root_meta(draft_root, draft_name, draft_path, cover_path, total_duration)
    print(f"draft_name={draft_name}")
    print(f"draft_path={draft_path}")
    print(f"root_meta_backup={backup if backup is not None else 'not_required'}")
    print(f"duration_us={total_duration}")
    return draft_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Jianying draft from images, captions, voice and BGM.")
    parser.add_argument("--manifest", type=Path, help="Path to manifest JSON.")
    parser.add_argument("--init-demo", type=Path, help="Create demo assets and manifest in this folder.")
    args = parser.parse_args()

    if args.init_demo:
        args.init_demo.mkdir(parents=True, exist_ok=True)
        make_demo_assets(args.init_demo)
        write_demo_manifest(args.init_demo / "manifest.json")
        print(f"demo_manifest={args.init_demo / 'manifest.json'}")
        return
    if not args.manifest:
        raise SystemExit("请传入 --manifest，或使用 --init-demo 生成示例项目。")
    build_draft(args.manifest)


if __name__ == "__main__":
    main()
