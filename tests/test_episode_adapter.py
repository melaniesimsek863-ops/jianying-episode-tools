import json
import shutil
import unittest
from pathlib import Path


class EpisodeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(__file__).parent / ".test_work" / self._testMethodName
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_convert_episode_preserves_shot_ranges_and_audio(self):
        from episode_to_jianying import convert_episode

        episode = {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "voice": "audio/voice.wav",
            "bgm": "audio/bgm.wav",
            "voice_volume": 1.0,
            "bgm_volume": 0.08,
            "shots": [
                {"image": "images/001.png", "duration": 2.5},
                {"image": "images/002.png", "duration": 3.0},
            ],
            "captions": [{"text": "字幕", "start": 0.0, "duration": 5.5}],
        }
        episode_path = self.work / "episode.json"
        episode_path.write_text(json.dumps(episode, ensure_ascii=False), encoding="utf-8")
        output_path = self.work / "jianying_manifest.json"

        result = convert_episode(episode_path, output_path, "life_copy_test")
        manifest = json.loads(result.read_text(encoding="utf-8"))

        self.assertEqual(manifest["draft_name"], "life_copy_test")
        self.assertEqual(manifest["images"], ["images/001.png", "images/002.png"])
        self.assertEqual(
            manifest["image_ranges"],
            [{"start": 0.0, "duration": 2.5}, {"start": 2.5, "duration": 3.0}],
        )
        self.assertEqual(manifest["voice"], "audio/voice.wav")
        self.assertEqual(manifest["bgm"], "audio/bgm.wav")
        self.assertEqual(manifest["captions"], episode["captions"])


if __name__ == "__main__":
    unittest.main()
