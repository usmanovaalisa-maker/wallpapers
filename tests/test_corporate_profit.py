import contextlib
import datetime as dt
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import corporate_profit as corporate
import day_results
import send_bitrix as send
import sheet_results

TODAY = dt.date(2026, 11, 24)


def row(article, amount, vendor="one"):
    return {"article": article, "accountId": 1074, "accountType": [0], "vendorCode": vendor,
            "profitWithoutExpense": amount, "profit": 999999}


class CorporateProfitTests(unittest.TestCase):
    def test_sums_only_selected_product_rows_including_old_vendor_codes_and_losses(self):
        payload = {"byProduct": [row(261657089, "100.49"), row(261657089, "20.01", "old"),
                                 row(44713360, "-30.00")], "stats": {"profitWithoutExpense": 99999999}}
        with patch.object(corporate, "request", return_value=payload) as request:
            result = corporate.collect(TODAY, token="test")
        body = request.call_args.args[0]
        self.assertEqual(body["dateFrom"], "2026-09-01")
        self.assertEqual(body["dateTo"], "2026-11-24")
        self.assertEqual(body["filters"], {"accountTypes": [0], "article": ["261657089", "44713360"]})
        self.assertEqual(result["amount"], "90.50")
        self.assertEqual(corporate.footer({"corporate_profit": result}),
                         "На новогодний корпоратив заработано 91 рублей.")
        self.assertEqual(corporate.season_start(dt.date(2027, 1, 5)), dt.date(2026, 9, 1))

    def test_reads_all_pages_and_rounds_only_after_adding_both_articles(self):
        pages = [{"byProduct": [row(261657089, "1.24"), row(44713360, "1.24")]}, {"byProduct": []}]
        with patch.object(corporate, "PAGE_SIZE", 2), patch.object(corporate, "request", side_effect=pages) as req:
            result = corporate.collect(TODAY, token="test")
        self.assertEqual(req.call_count, 2)
        self.assertEqual(req.call_args.args[0]["page"], 2)
        self.assertEqual(corporate.footer({"corporate_profit": result}),
                         "На новогодний корпоратив заработано 2 рублей.")

    def test_missing_invalid_foreign_or_repeated_rows_never_become_zero(self):
        good = [row(261657089, 0), row(44713360, "-10.5")]
        bad_cases = [None, [], good[:1], good + [row(42, 100)], good + [good[0]],
                     [row(261657089, None), good[1]], [row(261657089, "NaN"), good[1]],
                     [row(261657089, True), good[1]], [{**good[0], "accountType": [1]}, good[1]]]
        for rows in bad_cases:
            with self.subTest(rows=rows), patch.object(corporate, "request", return_value={"byProduct": rows}), \
                    self.assertRaises(corporate.CorporateProfitError):
                corporate.collect(TODAY, token="test")
        with patch.object(corporate, "request", return_value={"byProduct": good}):
            result = corporate.collect(TODAY, token="test")
        self.assertIn("−11 рублей", corporate.footer({"corporate_profit": result}))
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(corporate.CorporateProfitError):
            corporate.collect(TODAY)

    def test_waits_for_corporate_source_and_leaves_other_mailings_unchanged(self):
        def ready():
            return {"source_type": "google_sheet", "ready": True, "errors": [], "not_loaded": [], "sources": ["Google Sheets"]}
        env = {"RESULTS_SOURCE": "google_sheet", "NG_CORPORATE_PROFIT": "1"}
        with patch.dict(os.environ, env), patch.object(sheet_results, "collect", side_effect=lambda _: ready()), \
                patch.object(corporate, "collect", side_effect=corporate.CorporateProfitError("Сеть")):
            result = day_results.collect(TODAY)
        self.assertFalse(result["ready"])
        self.assertEqual(day_results.stats_line(result), "")
        with patch.dict(os.environ, {**env, "NG_CORPORATE_PROFIT": ""}), \
                patch.object(sheet_results, "collect", side_effect=lambda _: ready()), \
                patch.object(corporate, "collect") as read:
            self.assertTrue(day_results.collect(TODAY)["ready"])
        read.assert_not_called()

    def test_footer_is_last_once_and_financial_sum_stays_out_of_public_log_and_card(self):
        data = {"daily": {TODAY.isoformat(): {"steady": "Текст", "reaction_steady": "Пожелание",
                                              "occasion": "Повод", "occasion_title": "Тема", "occasion_icon": "heart"}}}
        results = {"ready": True, "level": "steady", "corporate_profit": {"amount": "123456.78"}}
        env = {"BITRIX_WEBHOOK_URL": "https://example.test/rest/1/test/", "BITRIX_DIALOG_ID": "chat42"}
        with patch.dict(os.environ, env, clear=True), patch.object(send, "todays_date", return_value=TODAY.isoformat()), \
                patch.object(send, "team_data", return_value=data), patch.object(send, "day_results", return_value=(results, "Статистика")), \
                patch.object(send, "call", return_value={}) as call, patch.object(send, "send_control"), \
                contextlib.redirect_stdout(io.StringIO()) as log:
            send.main()
        message = call.call_args.args[2]["MESSAGE"]
        footer = corporate.footer(results)
        self.assertTrue(message.endswith(footer))
        self.assertEqual(message.count(footer), 1)
        self.assertLess(message.index("Повод для радости"), message.index(footer))
        self.assertNotIn("123 457", log.getvalue())
        with patch.dict(os.environ, {**env, "CARD": "1"}, clear=True), \
                patch.object(send, "todays_date", return_value=TODAY.isoformat()), patch.object(send, "team_data", return_value=data), \
                patch.object(send, "day_results", return_value=(results, "Статистика")), \
                patch("make_card.make_card", return_value=Path("card.jpg")) as card, \
                contextlib.redirect_stdout(io.StringIO()):
            send.main()
        self.assertEqual(card.call_args.args[1], "Пожелание")


if __name__ == "__main__":
    unittest.main()
