#!/usr/bin/env python3
"""Licensing: seats are not free, allowances can overrun, windows can stall.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import unittest

import _fixtures  # noqa: F401
import licensing  # noqa: E402

# 90 days of measured history at $9/day -> $270/month reference.
PROFILE = {
    "source": "measured",
    "date_range": ["2026-01-01", "2026-04-01"],
    "total_cost": 810.0,
}

SEAT = {
    "model": "seat",
    "plan": "Claude Max",
    "seat_monthly_cost": 200.0,
    "other_workload_share": 0.5,
}


class TestValidation(unittest.TestCase):
    def test_model_is_required(self):
        with self.assertRaises(licensing.LicensingError) as ctx:
            licensing.normalise({})
        self.assertIn("licensing.model is required", str(ctx.exception))

    def test_unknown_model_rejected(self):
        with self.assertRaises(licensing.LicensingError):
            licensing.normalise({"model": "freemium"})

    def test_consumption_needs_nothing_else(self):
        out = licensing.normalise({"model": "consumption"})
        self.assertEqual(out["model"], "consumption")

    def test_seat_requires_its_cost(self):
        cfg = dict(SEAT)
        del cfg["seat_monthly_cost"]
        with self.assertRaises(licensing.LicensingError) as ctx:
            licensing.normalise(cfg)
        message = str(ctx.exception)
        self.assertIn("seat_monthly_cost is required", message)
        self.assertIn("A seat is not free", message)

    def test_seat_requires_other_workload_share(self):
        cfg = dict(SEAT)
        del cfg["other_workload_share"]
        with self.assertRaises(licensing.LicensingError) as ctx:
            licensing.normalise(cfg)
        self.assertIn("other_workload_share is required", str(ctx.exception))

    def test_share_must_be_a_fraction(self):
        for bad in (-0.1, 1.5):
            cfg = dict(SEAT)
            cfg["other_workload_share"] = bad
            with self.assertRaises(licensing.LicensingError):
                licensing.normalise(cfg)

    def test_seat_prices_are_not_hardcoded(self):
        # A stale price table would silently misattribute every seat estimate.
        with open(licensing.__file__) as fh:
            source = fh.read()
        for suspicious in ("= 20.0", "= 100.0", "= 200.0", "= 30.0"):
            self.assertNotIn(suspicious, source)
        self.assertIn("NOT hardcoded", source)


class TestConsumption(unittest.TestCase):
    def test_notional_equals_billed(self):
        out = licensing.attribute(
            500.0, licensing.normalise({"model": "consumption"}), PROFILE)
        self.assertTrue(out["billed"])
        self.assertEqual(out["cost"], 500.0)

    def test_renders_as_a_charge(self):
        md = licensing.render_markdown(licensing.attribute(
            500.0, licensing.normalise({"model": "consumption"}), PROFILE))
        self.assertIn("Consumption billing", md)
        self.assertIn("expected charge", md)


class TestSeatAttribution(unittest.TestCase):
    def test_monthly_reference_from_history(self):
        self.assertAlmostEqual(
            licensing.monthly_reference(PROFILE), 270.0, places=0)

    def test_short_history_yields_no_reference(self):
        self.assertIsNone(licensing.monthly_reference(
            {"source": "measured", "date_range": ["2026-01-01", "2026-01-05"],
             "total_cost": 40.0}))

    def test_published_baseline_yields_no_reference(self):
        self.assertIsNone(licensing.monthly_reference(
            {"source": "published-baseline", "total_cost": 100.0}))

    def test_seat_is_not_reported_as_free(self):
        out = licensing.attribute(135.0, licensing.normalise(SEAT), PROFILE)
        self.assertFalse(out["billed"])
        self.assertIsNotNone(out["attributable_cost"])
        self.assertGreater(out["attributable_cost"], 0,
                           "a seat-based build must not be reported as $0")

    def test_attribution_is_seat_cost_times_allowance_share(self):
        # $135 of a $270 month = 50% of the allowance = 50% of a $200 seat.
        out = licensing.attribute(135.0, licensing.normalise(SEAT), PROFILE)
        self.assertAlmostEqual(out["allowance_share"], 0.5, places=2)
        self.assertAlmostEqual(out["attributable_cost"], 100.0, places=0)

    def test_seats_multiply_the_attributable_cost(self):
        cfg = dict(SEAT)
        cfg["seats"] = 4
        out = licensing.attribute(135.0, licensing.normalise(cfg), PROFILE)
        self.assertAlmostEqual(out["attributable_cost"], 400.0, places=0)

    def test_overrun_detected_against_other_workload(self):
        # 50% of the month, plus 50% already committed, is exactly full.
        out = licensing.attribute(162.0, licensing.normalise(SEAT), PROFILE)
        self.assertTrue(out["overruns"])
        self.assertGreater(out["overrun_cost"], 0)

    def test_headroom_when_it_fits(self):
        out = licensing.attribute(54.0, licensing.normalise(SEAT), PROFILE)
        self.assertFalse(out["overruns"])
        self.assertAlmostEqual(out["headroom_share"], 0.3, places=2)

    def test_no_reference_means_no_invented_denominator(self):
        thin = {"source": "measured",
                "date_range": ["2026-01-01", "2026-01-03"], "total_cost": 10.0}
        out = licensing.attribute(135.0, licensing.normalise(SEAT), thin)
        self.assertIsNone(out["allowance_share"])
        self.assertIsNone(out["attributable_cost"])
        self.assertIn("could not be computed", out["note"])


class TestSeatRendering(unittest.TestCase):
    def setUp(self):
        self.out = licensing.attribute(162.0, licensing.normalise(SEAT), PROFILE)
        self.md = licensing.render_markdown(self.out)

    def test_states_the_seat_is_not_free(self):
        self.assertIn("the seat is not free", self.md)
        self.assertIn("Attributable cost of this build", self.md)

    def test_shows_overrun_and_its_cost(self):
        self.assertIn("Allowance overrun", self.md)
        self.assertIn("exceeds the allowance", self.md)

    def test_warns_about_shorter_windows(self):
        self.assertIn("Window risk", self.md)
        self.assertIn("5-hour rolling", self.md)
        self.assertIn("weekly", self.md)

    def test_concentrated_build_gets_a_stronger_warning(self):
        cfg = dict(SEAT)
        cfg["concentrated"] = True
        md = licensing.render_markdown(
            licensing.attribute(54.0, licensing.normalise(cfg), PROFILE))
        self.assertIn("marked as concentrated", md)
        self.assertIn("expect to hit shorter windows", md)

    def test_notional_value_is_labelled_as_not_a_charge(self):
        self.assertIn("not a charge", self.md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
