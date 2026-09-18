# Publication Notes

Prototype tools for converting an episode manifest into a render plan and a
Jianying draft. Not affiliated with Jianying or CapCut. Historical local draft
testing used Jianying 6.0.1.11779; compatibility with other versions is unverified.

Install Python and `python -m pip install -r requirements.txt`. FFmpeg is an
external prerequisite for actual MP4 rendering. The application uses the current
user's LOCALAPPDATA directory for the default draft root. Override the draft root
in your manifest when needed. Avoid replacing existing drafts.

Only scripts and synthetic test fixtures are included. No course material,
personal media, voice-cloning models or third-party binaries are distributed.
The test suite validates manifests and render plans, not visual quality or the
current Jianying graphical interface.
