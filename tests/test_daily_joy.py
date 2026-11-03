import contextlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import daily_phrases as daily


class DailyJoyTests(unittest.TestCase):
    def setUp(self):
        self.obj = {key: "Тёплое пожелание команде." for key in daily.MAIN_KEYS + daily.REACTION_KEYS}
        self.obj.update(occasion="Устройте чайную паузу.", occasion_title="Чайная пауза",
                        occasion_icon="tea", occasion_kind="small_joy", occasion_sources=[])

    def test_small_joy_needs_no_holiday_source_or_image(self):
        self.assertTrue(daily.prepared(self.obj))
        self.assertNotIn("illustration", self.obj)

    def test_holiday_needs_source_and_symbol(self):
        holiday = {**self.obj, "occasion_kind": "holiday"}
        self.assertFalse(daily.prepared(holiday))
        holiday["occasion_sources"] = ["https://example.com/calendar/3-november"]
        self.assertTrue(daily.prepared(holiday))
        holiday["occasion_icon"] = "external-image-url"
        self.assertFalse(daily.prepared(holiday))

    def test_weekends_are_prepared_without_discarding_local_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / ".github").mkdir()
            empty = type("Result", (), {"stdout": ""})()
            with patch.object(daily, "ROOT", root), patch.object(daily, "git", return_value=empty) as git, \
                    patch.object(daily, "load", return_value={"daily": {}, "calendar": {}}), \
                    patch.object(daily, "tomorrow", return_value="2026-11-07"), contextlib.redirect_stdout(io.StringIO()) as out:
                daily.cmd_start()
            self.assertIn("нужно написать", out.getvalue())
            self.assertFalse(any("reset" in call.args for call in git.call_args_list))
        dirty = type("Result", (), {"stdout": " M wishes/ng.json"})()
        with patch.object(daily, "git", return_value=dirty) as git, self.assertRaises(SystemExit):
            daily.cmd_start()
        self.assertEqual(git.call_count, 1)


if __name__ == "__main__":
    unittest.main()
