import json
import shutil
import unittest
from pathlib import Path


class RenderEpisodeTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(__file__).parent / ".test_work" / self._testMethodName
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def make_episode(self, root: Path) -> Path:
        (root / "images").mkdir()
        (root / "audio").mkdir()
        for name in ("001.png", "002.png"):
            (root / "images" / name).write_bytes(b"image")
        (root / "audio" / "voice.wav").write_bytes(b"voice")
        episode = {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "voice": "audio/voice.wav",
            "shots": [
                {"image": "images/001.png", "duration": 2.5},
                {"image": "images/002.png", "duration": 3.0},
            ],
            "captions": [
                {"text": "第一句字幕", "start": 0.0, "duration": 2.5},
                {"text": "第二句字幕", "start": 2.5, "duration": 3.0},
            ],
        }
        path = root / "episode.json"
        path.write_text(json.dumps(episode, ensure_ascii=False), encoding="utf-8")
        return path

    def test_build_render_plan_contains_vertical_layout_and_subtitles(self):
        from render_episode import build_render_plan

        episode_path = self.make_episode(self.work)
        plan = build_render_plan(episode_path, self.work / "out.mp4", "ffmpeg.exe")

        self.assertEqual(plan.duration, 5.5)
        self.assertEqual(len(plan.images), 2)
        self.assertIn("gblur=sigma=32", plan.filter_complex)
        self.assertIn("overlay=0:360", plan.filter_complex)
        self.assertIn("concat=n=2:v=1:a=0", plan.filter_complex)
        self.assertIn("ass=", plan.filter_complex)
        self.assertIn("-loop", plan.command)
        self.assertEqual(plan.command[-1], str((self.work / "out.mp4").resolve()))

    def test_wrap_caption_breaks_long_chinese_text(self):
        from render_episode import wrap_caption

        wrapped = wrap_caption("今天体验的人生副本是舔狗醒悟后的一生", width=10)
        self.assertEqual(wrapped, "今天体验的人生副本是\\N舔狗醒悟后的一生")


if __name__ == "__main__":
    unittest.main()
