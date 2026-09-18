# Validation

Checked on 2026-09-18: `python -m unittest discover -s tests -v` passed all
6 tests in 1.142 seconds on the staged source.

Checks cover caption style, blurred canvas, missing root metadata, shot/audio
timing, FFmpeg render-plan construction and caption wrapping. These tests use
synthetic inputs and do not render a real MP4 or open the current Jianying UI.

The publication copy removes a fixed private dependency path and derives the
default draft root from the current user's LOCALAPPDATA environment variable.
Existing local Pillow and pyJianYingDraft dependencies were reused for testing;
a clean dependency install was not exercised. Dependency versions are not yet
pinned, so editor/library compatibility needs validation in each environment.
