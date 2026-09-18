import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderPlan:
    command: list[str]
    filter_complex: str
    duration: float
    images: list[Path]
    ass_path: Path


def read_episode(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def wrap_caption(text: str, width: int = 15) -> str:
    clean = "".join(str(text).strip().splitlines())
    return r"\N".join(clean[i : i + width] for i in range(0, len(clean), width))


def ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cents = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cents:02d}"


def escape_ass_text(text: str) -> str:
    return wrap_caption(text.replace("{", r"\{").replace("}", r"\}"))


def write_ass(path: Path, captions: list[dict], width: int, height: int) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Microsoft YaHei,54,&H00FFFFFF,&H000000FF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,4,0,2,72,72,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in captions:
        start = float(item["start"])
        end = start + float(item["duration"])
        events.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Main,,0,0,0,,{escape_ass_text(item['text'])}"
        )
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")


def ffmpeg_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def build_render_plan(manifest_path: Path, output_path: Path, ffmpeg_path: str) -> RenderPlan:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    episode = read_episode(manifest_path)
    width = int(episode.get("width", 1080))
    height = int(episode.get("height", 1920))
    fps = int(episode.get("fps", 30))
    shots = episode.get("shots") or []
    if not shots:
        raise ValueError("episode.json 至少需要一个 shot")

    images = [resolve(base, shot.get("image")) for shot in shots]
    if any(path is None for path in images):
        raise ValueError("每个 shot 都必须提供 image")
    images = [path for path in images if path is not None]
    durations = [float(shot["duration"]) for shot in shots]
    if any(duration <= 0 for duration in durations):
        raise ValueError("shot duration 必须大于 0")
    duration = round(sum(durations), 3)

    voice = resolve(base, episode.get("voice"))
    if voice is None:
        raise ValueError("episode.json 必须提供 voice")
    bgm = resolve(base, episode.get("bgm"))
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path = output_path.with_suffix(".ass")
    write_ass(ass_path, episode.get("captions") or [], width, height)

    command = [str(ffmpeg_path), "-y"]
    for image, shot_duration in zip(images, durations):
        command.extend(["-loop", "1", "-framerate", str(fps), "-t", f"{shot_duration:.3f}", "-i", str(image)])
    voice_index = len(images)
    command.extend(["-i", str(voice)])
    bgm_index = None
    if bgm is not None:
        bgm_index = voice_index + 1
        command.extend(["-stream_loop", "-1", "-i", str(bgm)])

    filters = []
    for index, shot_duration in enumerate(durations):
        filters.append(f"[{index}:v]split=2[bg{index}in][fg{index}in]")
        filters.append(
            f"[bg{index}in]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},gblur=sigma=32,eq=brightness=-0.30:saturation=0.72[bg{index}]"
        )
        filters.append(
            f"[fg{index}in]scale={width}:608:force_original_aspect_ratio=decrease,"
            f"pad={width}:608:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"zoompan=z='min(zoom+0.00035,1.045)':d=1:s={width}x608:fps={fps}[fg{index}]"
        )
        filters.append(
            f"[bg{index}][fg{index}]overlay=0:360:shortest=1,"
            f"trim=duration={shot_duration:.3f},setpts=PTS-STARTPTS[s{index}]"
        )
    concat_inputs = "".join(f"[s{i}]" for i in range(len(images)))
    filters.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[joined]")
    filters.append(f"[joined]ass='{ffmpeg_filter_path(ass_path)}'[vout]")

    voice_volume = float(episode.get("voice_volume", 1.0))
    filters.append(
        f"[{voice_index}:a]aresample=48000,volume={voice_volume:.3f},"
        f"atrim=duration={duration:.3f},apad=pad_dur={duration:.3f},"
        f"afade=t=in:st=0:d=0.08,afade=t=out:st={max(duration - 0.25, 0):.3f}:d=0.25[voice]"
    )
    if bgm_index is not None:
        bgm_volume = float(episode.get("bgm_volume", 0.10))
        filters.append(
            f"[{bgm_index}:a]aresample=48000,volume={bgm_volume:.3f},"
            f"atrim=duration={duration:.3f},afade=t=in:st=0:d=0.8,"
            f"afade=t=out:st={max(duration - 1.2, 0):.3f}:d=1.2[music]"
        )
        filters.append("[voice][music]amix=inputs=2:duration=first:dropout_transition=1,alimiter=limit=0.95[aout]")
    else:
        filters.append("[voice]anull[aout]")

    filter_complex = ";".join(filters)
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{duration:.3f}",
            str(output_path),
        ]
    )
    return RenderPlan(command, filter_complex, duration, images, ass_path)


def render_episode(manifest_path: Path, output_path: Path, ffmpeg_path: str) -> Path:
    plan = build_render_plan(manifest_path, output_path, ffmpeg_path)
    subprocess.run(plan.command, check=True)
    return output_path.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a vertical life-copy video from episode.json")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True)
    args = parser.parse_args()
    output = render_episode(args.manifest, args.output, args.ffmpeg)
    print(output)


if __name__ == "__main__":
    main()
