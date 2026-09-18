import shutil
import unittest
from pathlib import Path

from PIL import Image


class DraftStylingTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(__file__).parent / ".test_work" / self._testMethodName
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_video_segment_uses_blurred_canvas_and_gentle_scale(self):
        from make_draft import build_video_segment, jy

        image_path = self.work / "frame.png"
        Image.new("RGB", (1600, 900), (30, 40, 50)).save(image_path)
        material = jy.VideoMaterial(str(image_path))

        segment = build_video_segment(material, 0, 2_000_000, True, 1.045, 0.32)

        self.assertIsNotNone(segment.background_filling)
        self.assertEqual(segment.background_filling.fill_type, "canvas_blur")
        self.assertEqual(segment.background_filling.blur, 0.32)
        self.assertEqual(len(segment.common_keyframes), 1)

    def test_caption_segment_is_bold_centered_and_below_image(self):
        from make_draft import build_caption_segment

        segment = build_caption_segment("字幕", 0, 2_000_000)

        self.assertTrue(segment.style.bold)
        self.assertEqual(segment.style.align, 1)
        self.assertTrue(segment.style.auto_wrapping)
        self.assertEqual(segment.clip_settings.transform_y, -0.62)
        self.assertIsNotNone(segment.border)

    def test_missing_root_meta_is_supported_for_jianying_6(self):
        from make_draft import register_root_meta

        draft_root = self.work / "draft_root"
        draft_path = draft_root / "sample"
        draft_path.mkdir(parents=True)
        cover_path = draft_path / "draft_cover.jpg"
        Image.new("RGB", (16, 9), (30, 40, 50)).save(cover_path)

        backup = register_root_meta(draft_root, "sample", draft_path, cover_path, 2_000_000)

        self.assertIsNone(backup)


if __name__ == "__main__":
    unittest.main()
