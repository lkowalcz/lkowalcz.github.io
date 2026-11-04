"""Regression checks for ADV denominators, incomplete days, and month rollover."""

import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "updater", Path(__file__).with_name("update-iex-notional.py")
)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)

EQUITIES = "Date,Trading Market Centre,Market\n"
OPTIONS = "Day,Market Participant,Total Option Contracts\n"


class VolumeTests(unittest.TestCase):
    def test_equities_average_excludes_prior_month_and_today(self):
        rows = EQUITIES + (
            "2026-10-30,Investors Exchange (V),900\n"
            "2026-11-02,Investors Exchange (V),100\n"
            "2026-11-02,Other Exchange,999\n"
            "2026-11-03,Investors Exchange (V),300\n"
            "2026-11-04,Investors Exchange (V),1\n"
        )
        result = updater.parse_mtd("\ufeff" + rows, "equities", date(2026, 11, 4))
        self.assertEqual(result, {
            "month": "2026-11", "through": "2026-11-03",
            "trading_days": 2, "value": 200,
        })

    def test_weekend_and_holiday_do_not_count_as_trading_days(self):
        rows = OPTIONS + (
            "2026-11-25,Investors Exchange (V),100\n"
            "2026-11-27,IEX Options (V),300\n"
        )
        result = updater.parse_mtd(rows, "options", date(2026, 11, 30))
        self.assertEqual(result["trading_days"], 2)
        self.assertEqual(result["value"], 200)
        self.assertEqual(result["through"], "2026-11-27")

    def test_options_launch_month_matches_cboe_denominator(self):
        rows = OPTIONS + (
            "2026-10-01,Other Exchange,10000\n"
            "2026-10-02,Investors Exchange (V),282\n"
        )
        result = updater.parse_mtd(rows, "options", date(2026, 10, 3))
        self.assertEqual(result["value"], 141)
        self.assertEqual(result["trading_days"], 2)

    def test_zero_volume_is_a_valid_session(self):
        result = updater.parse_mtd(
            OPTIONS + "2026-11-02,Investors Exchange (V),0\n",
            "options", date(2026, 11, 3),
        )
        self.assertEqual(result["value"], 0)

    def test_no_new_month_sessions_means_no_mtd_point(self):
        result = updater.parse_mtd(
            OPTIONS + "2026-10-30,Investors Exchange (V),100\n",
            "options", date(2026, 11, 2),
        )
        self.assertIsNone(result)

    def test_missing_venue_is_not_silently_counted_as_zero(self):
        with self.assertRaisesRegex(RuntimeError, "missing IEX"):
            updater.parse_mtd(
                OPTIONS + "2026-11-02,Other Exchange,100\n",
                "options", date(2026, 11, 3),
            )

    def test_rejects_duplicate_sessions_and_invalid_values(self):
        duplicate = "2026-11-02,Investors Exchange (V),100\n" * 2
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            updater.parse_mtd(OPTIONS + duplicate, "options", date(2026, 11, 3))
        for value in ("NaN", "inf", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                updater.parse_mtd(
                    OPTIONS + f"2026-11-02,Investors Exchange (V),{value}\n",
                    "options", date(2026, 11, 3),
                )

    def test_rejects_changed_csv_schema(self):
        with self.assertRaisesRegex(RuntimeError, "columns"):
            updater.parse_mtd("<html>Unavailable</html>", "options", date(2026, 11, 3))

    def test_rollover_fetches_final_average_instead_of_promoting_mtd(self):
        old = {"start": "2026-10", "values": [], "mtd": {
            "month": "2026-10", "through": "2026-10-29", "value": 80,
        }}
        with patch.object(updater, "fetch_month_adv", return_value=100) as monthly, \
                patch.object(updater, "fetch_mtd", return_value=None), \
                patch.object(updater.time, "sleep"):
            new = updater.update_series("options", old, date(2026, 11, 1))
        monthly.assert_called_once_with("options", 2026, 10)
        self.assertEqual(new["values"], [100])
        self.assertIsNone(new["mtd"])
        self.assertEqual(old["values"], [])

    def test_year_rollover_and_missed_months(self):
        old = {"start": "2026-10", "values": [100]}
        mtd = {"month": "2027-01", "through": "2027-01-04", "value": 400}
        with patch.object(updater, "fetch_month_adv", side_effect=[200, 300]) as monthly, \
                patch.object(updater, "fetch_mtd", return_value=mtd), \
                patch.object(updater.time, "sleep"):
            new = updater.update_series("options", old, date(2027, 1, 5))
        self.assertEqual([call.args for call in monthly.call_args_list], [
            ("options", 2026, 11), ("options", 2026, 12),
        ])
        self.assertEqual(new["values"], [100, 200, 300])
        self.assertEqual(new["mtd"], mtd)

    def test_daily_refresh_replaces_mtd_and_is_idempotent(self):
        mtd = {"month": "2026-11", "through": "2026-11-03", "value": 300}
        old = {"start": "2026-10", "values": [100], "mtd": {
            "month": "2026-11", "through": "2026-11-02", "value": 200,
        }}
        with patch.object(updater, "fetch_month_adv") as monthly, \
                patch.object(updater, "fetch_mtd", return_value=mtd):
            new = updater.update_series("options", old, date(2026, 11, 4))
            again = updater.update_series("options", new, date(2026, 11, 4))
        monthly.assert_not_called()
        self.assertEqual(new["values"], [100])
        self.assertEqual(new["mtd"], mtd)
        self.assertEqual(new, again)

    def test_stale_csv_cannot_erase_newer_mtd(self):
        old = {"start": "2026-10", "values": [100], "mtd": {
            "month": "2026-11", "through": "2026-11-03", "value": 300,
        }}
        for stale in (None, {"through": "2026-11-02"}):
            with patch.object(updater, "fetch_mtd", return_value=stale), \
                    self.assertRaisesRegex(RuntimeError, "regressed"):
                updater.update_series("options", old, date(2026, 11, 4))

    def test_monthly_parser_validates_date_and_selects_contracts(self):
        blob = {metric: {"integrated": {"y": {"data": [{
            "mktname": "iexoptionsv", "avg_value": value,
        }]}}} for metric, value in (("Volume", 123), ("Notional Value", 999))}
        html = "var cal_dt = '2026-11-01';\nvar mtd_data = " + json.dumps(blob) + ";\n"
        with patch.object(updater, "fetch", return_value=html):
            self.assertEqual(updater.fetch_month_adv("options", 2026, 10), 123)
            with self.assertRaisesRegex(RuntimeError, "unexpected Cboe"):
                updater.fetch_month_adv("options", 2026, 9)


if __name__ == "__main__":
    unittest.main()
