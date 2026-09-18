# Jianying Episode Tools

Prototype utilities that use one episode manifest to prepare a local MP4 render
and a Jianying draft. See [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) for scope.

## Requirements

Python, Pillow, pyJianYingDraft, and FFmpeg for actual MP4 rendering.
Jianying desktop is needed to open generated drafts. Compatibility was explored
locally on Jianying 6.0.1.11779; other versions are not certified.

```powershell
python -m pip install -r requirements.txt
python make_draft.py --help
python episode_to_jianying.py --help
python render_episode.py --help
```

## Episode Format

Paths are relative to the episode file unless an absolute path is supplied.

```json
{
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "voice": "audio/narration.wav",
  "shots": [{"image": "images/001.png", "duration": 2.5}],
  "captions": [{"text": "Example caption", "start": 0.0, "duration": 2.5}]
}
```

## Render and Export

```powershell
python render_episode.py --manifest episode.json --output output/final.mp4 --ffmpeg ffmpeg
python episode_to_jianying.py --episode episode.json --output jianying_manifest.json --draft-name example
python make_draft.py --manifest jianying_manifest.json
```

The default draft location follows the current user's LOCALAPPDATA environment
variable. Set `draft_root` in the draft manifest to a test directory before
trying the tool with an installed editor. Preserve your existing drafts.

## Tests and Limits

```powershell
python -m unittest discover -s tests -v
```

Tests cover manifest timing, draft styling and render-plan construction. They do
not prove actual MP4 playback or current editor GUI compatibility. See
[VALIDATION.md](VALIDATION.md) for the current check results.

Use media you have permission to process. This source release includes no user
photos, voices, music, course content, generated samples or model binaries.
