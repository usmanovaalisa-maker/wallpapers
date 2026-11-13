import csv
import datetime as dt
import io
import json
import os
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import day_results
import sheet_results as sheet


TODAY = dt.date(2026, 11, 4)


def fixture():
    return [["Свод ВБ + Озон: динамика по дням"], ["Новогодка"],
            ["Сезон", "НГ 2027", "", "", "Текущий сезон: данные по 03.11.2026"], ["Описание"],
            ["", "Заказы, ₽", "", "", "Продажи, ₽", "", "", "Выкуп, %", "", "", "Прибыль без опер. расх., ₽", "", "", "Чистая маржа, %", "", ""],
            ["Дата"] + ["Итого", "ВБ", "Озон"] * 5,
            ["02.11.26", "900", "700", "200", "500", "400", "100", "80%", "75%", "100%", "70", "80", "−10", "14%", "20%", "−10%"],
            ["03.11.26", "1\u00a0000", "750", "250", "600", "450", "150", "82,9%", "83,0%", "78,6%", "90", "120", "−30", "12,7%", "20%", "−40%"]]


def as_csv(rows):
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue()


class SheetResultsTests(unittest.TestCase):
    def test_precise_cells_drive_totals_and_inconsistent_reads_are_rejected(self):
        rows = fixture()
        raw_rows = []
        for row in rows[6:]:
            date = sheet.date_value(row[0])
            cells = [{"v": f"Date({date.year},{date.month-1},{date.day})"}]
            cells += [{"v": float(sheet.number(v, 7 <= i <= 9))} for i, v in enumerate(row[1:], 1)]
            raw_rows.append({"c": cells})
        raw_rows[-1]["c"][1]["v"] = 1000.12
        raw_rows[-1]["c"][2]["v"] = 750.12
        raw_rows[-1]["c"][13]["v"] = .127145
        payload = {"status": "ok", "table": {"cols": [{"type": "date"}] + [{"type": "number"}] * 15,
                                               "rows": raw_rows}}
        callback = "/*O_o*/\ngoogle.visualization.Query.setResponse(" + json.dumps(payload) + ");"
        text = sheet.precise_csv(as_csv(rows), callback)
        result = sheet.collect(TODAY, text)
        self.assertTrue(result["ready"])
        self.assertEqual(result["period_orders_amount"]["total"], 1900.12)
        self.assertEqual(result["marketplaces"]["total"]["margin"], .127145)
        raw_rows[-1]["c"][1]["v"] = 1100
        with self.assertRaises(sheet.SheetError):
            sheet.precise_csv(as_csv(rows), json.dumps(payload))

    def test_maps_marketplaces_preserving_table_total_and_negative_profit(self):
        result = sheet.collect(TODAY, as_csv(fixture()))
        self.assertTrue(result["ready"])
        self.assertEqual(result["marketplaces"]["wb"]["orders_amount"], 750)
        self.assertEqual(result["marketplaces"]["ozon"]["profit"], -30)
        self.assertEqual(result["marketplaces"]["total"]["buyout"], 0.829)
        self.assertEqual(result["level"], "up")
        message = day_results.stats_line(result)
        self.assertLess(message.index("[B]ВБ[/B]"), message.index("[B]Озон[/B]"))
        self.assertLess(message.index("[B]Озон[/B]"), message.index("[B]Итого[/B]"))
        self.assertIn("−30 ₽", message)
        self.assertIn("82,9%", message)
        self.assertNotIn("заказов на", message)  # Количество заказов в источнике не дано.
        self.assertIn("02.11.2026", message)  # Накопительный итог — только за фактический период.

    def test_profit_label_matches_updated_sheet_without_changing_values(self):
        rows = fixture()
        rows[4][10] = "Чистая прибыль, ₽"
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertTrue(result["ready"])
        self.assertEqual(result["marketplaces"]["ozon"]["profit"], -30)
        message = sheet.stats_line(result)
        self.assertIn("чистая прибыль: −30 ₽", message)
        self.assertNotIn("без опер.", message)
        rows[4][10] = "Валовая прибыль, ₽"
        self.assertFalse(sheet.collect(TODAY, as_csv(rows))["ready"])

    def test_margin_is_read_per_marketplace_and_placed_after_profit(self):
        rows = fixture()
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertTrue(result["ready"])
        self.assertEqual(result["marketplaces"]["total"]["margin"], .127)
        self.assertEqual(result["marketplaces"]["wb"]["margin"], .20)
        self.assertEqual(result["marketplaces"]["ozon"]["margin"], -.40)
        message = sheet.stats_line(result)
        self.assertIn("90 ₽ (маржинальность: 12,7%)", message)
        self.assertIn("−30 ₽ (маржинальность: −40,0%)", message)
        rows[-1][13:16] = ["0%", "", "−200%"]
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertTrue(result["ready"])
        self.assertIn("маржинальность: 0,0%", sheet.stats_line(result))
        self.assertIn("маржинальность: нет данных", sheet.stats_line(result))
        self.assertIn("маржинальность: −200,0%", sheet.stats_line(result))
        for kind in ("header", "order", "formula"):
            rows = fixture()
            if kind == "header": rows[4][13] = "ДРР, %"
            if kind == "order": rows[5][14] = "Озон"
            if kind == "formula": rows[-1][15] = "#DIV/0!"
            with self.subTest(kind=kind):
                self.assertFalse(sheet.collect(TODAY, as_csv(rows))["ready"])

    def test_zeros_are_data_and_empty_buyout_is_not_zero_percent(self):
        rows = fixture()
        rows[-1] = ["03.11.26"] + ["0"] * 6 + [""] * 3 + ["0"] * 3 + [""] * 3
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertTrue(result["ready"])
        self.assertIn("Заказы: 0 ₽", sheet.stats_line(result))
        self.assertIn("Выкуп: нет данных", sheet.stats_line(result))
        self.assertIn("прибыль без опер. расходов: 0 ₽", sheet.stats_line(result))

    def test_bad_sources_do_not_fall_back_to_truestats(self):
        with patch.dict(os.environ, {"RESULTS_SOURCE": "google_sheet"}), \
                patch.object(sheet, "read_csv", side_effect=sheet.SheetError("Нет доступа")), \
                patch.object(day_results, "truestats") as legacy:
            result = day_results.collect(TODAY)
        self.assertFalse(result["ready"])
        self.assertEqual(day_results.stats_line(result), "")
        legacy.assert_not_called()

    def test_rejects_stale_wrong_season_missing_date_and_formula_errors(self):
        for kind in ("stale", "season", "date", "formula", "total", "headers", "duplicate", "stamp"):
            rows = fixture()
            if kind == "stale": rows[2][4] = "Текущий сезон: данные по 02.11.2026"
            if kind == "season": rows[2][1] = "НГ 2026"
            if kind == "date": rows.pop()
            if kind == "formula": rows[-1][2] = "#REF!"
            if kind == "total": rows[-1][1] = "1500"
            if kind == "headers": rows[5][2] = "Озон"
            if kind == "duplicate": rows.append(rows[-1][:])
            if kind == "stamp": rows[2][4] = "Текущий сезон: данные по 32.11.2026"
            with self.subTest(kind=kind):
                result = sheet.collect(TODAY, as_csv(rows))
                self.assertFalse(result["ready"])
                self.assertEqual(sheet.stats_line(result), "")

    def test_future_rows_are_excluded_and_gap_suppresses_accumulated_total(self):
        rows = fixture()
        future = rows[-1][:]
        future[0] = "04.11.26"
        future[1:4] = ["3000", "2000", "1000"]
        rows.append(future)
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertEqual(result["period_orders_amount"]["total"], 1900)
        rows[6][0] = "01.11.26"
        result = sheet.collect(TODAY, as_csv(rows))
        self.assertTrue(result["ready"])
        self.assertIsNone(result["period_orders_amount"])

    def test_one_ruble_rounding_difference_is_allowed_but_not_two(self):
        rows = fixture()
        rows[-1][1] = "1001"
        self.assertTrue(sheet.collect(TODAY, as_csv(rows))["ready"])
        rows[-1][1] = "1002"
        self.assertFalse(sheet.collect(TODAY, as_csv(rows))["ready"])


if __name__ == "__main__":
    unittest.main()
