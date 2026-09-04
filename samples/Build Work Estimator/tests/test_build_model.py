#!/usr/bin/env python3
"""Which model builds it, and whether the repricing can be trusted.

Author: Dewain Robinson

The rescale multiplies a MEASURED number by a ratio of PUBLISHED rates. That
is only defensible if three things hold, and each has a test here:

  * it returns the measured number untouched when the model matches the
    calibration mix -- the anchor property,
  * it decomposes by cost component rather than by headline input rate, which
    is the difference between right and 98% wrong on a model whose cache-read
    multiplier differs,
  * it refuses a model the build platform cannot actually run.
"""

__author__ = "Dewain Robinson"

import json
import os
import sys
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))

import build_model  # noqa: E402
import estimate  # noqa: E402
import github_copilot as gh  # noqa: E402
import rates  # noqa: E402
import render_report as rr  # noqa: E402
import assumptions  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402

with open(os.path.join(SAMPLE, "examples", "calibration-profile.json")) as fh:
    REAL_PROFILE = json.load(fh)

CAL_MIX = {"claude-opus-5": 0.55, "claude-sonnet-5": 0.45}

#: The small fixture profile records no model mix, so it correctly takes the
#: disclosure path. Tests that need a RESCALE need a profile that can support
#: one -- which is itself the fallback behaving as designed.
REPRICEABLE = dict(
    PROFILE,
    model_mix=dict(CAL_MIX),
    component_shares={"cache_read": 0.66, "cache_write": 0.25,
                      "output": 0.09},
)


class TestAnchorProperty(unittest.TestCase):
    """Declaring the calibration mix must change nothing at all."""

    def test_matching_mix_gives_exactly_one(self):
        info = build_model.resolve(
            {"build_model": dict(CAL_MIX)}, REAL_PROFILE, "claude-code")
        self.assertTrue(info["repriced"])
        self.assertEqual(info["ratio"], 1.0,
                         "a matching mix must not perturb the measured cost")

    def test_matching_mix_returns_the_measured_cost_untouched(self):
        info = build_model.resolve(
            {"build_model": dict(CAL_MIX)}, REAL_PROFILE, "claude-code")
        self.assertEqual(info["cost_per_turn"],
                         REAL_PROFILE["cost_per_main_turn"])

    def test_weights_need_not_be_normalised(self):
        """55/45 and 11/9 are the same mix."""
        a = build_model.resolve({"build_model": dict(CAL_MIX)},
                                REAL_PROFILE, "claude-code")
        b = build_model.resolve(
            {"build_model": {"claude-opus-5": 11, "claude-sonnet-5": 9}},
            REAL_PROFILE, "claude-code")
        self.assertEqual(a["ratio"], b["ratio"])


class TestRatioDirection(unittest.TestCase):
    def test_a_pricier_model_costs_more(self):
        info = build_model.resolve({"build_model": "claude-opus-5"},
                                   REAL_PROFILE, "claude-code")
        self.assertGreater(info["ratio"], 1.0)
        self.assertGreater(info["cost_per_turn"],
                           REAL_PROFILE["cost_per_main_turn"])

    def test_a_cheaper_model_costs_less(self):
        info = build_model.resolve({"build_model": "claude-haiku-4-5"},
                                   REAL_PROFILE, "claude-code")
        self.assertLess(info["ratio"], 1.0)

    def test_the_ratio_is_the_published_rate_ratio(self):
        """Opus vs the blend, computed independently of the module."""
        blended_input = 0.55 * 5.00 + 0.45 * 2.00
        expected = 5.00 / blended_input
        info = build_model.resolve({"build_model": "claude-opus-5"},
                                   REAL_PROFILE, "claude-code")
        self.assertAlmostEqual(info["ratio"], expected, places=6)


class TestComponentDecompositionEarnsItsKeep(unittest.TestCase):
    """The case a headline-input-rate ratio gets badly wrong.

    Fable 5.1 reads cache at 0.025x rather than 0.10x, and cache reads are
    ~66% of the bill. Scaling by the input rate alone would nearly double the
    answer, which is why the rescale decomposes by component.
    """

    def test_fable_is_not_priced_by_input_rate_alone(self):
        info = build_model.resolve({"build_model": "claude-fable-5-1"},
                                   REAL_PROFILE, "claude-code")
        naive = 10.00 / (0.55 * 5.00 + 0.45 * 2.00)
        self.assertGreater(naive / info["ratio"], 1.9,
                           "the naive ratio should be ~2x the correct one")
        self.assertAlmostEqual(info["ratio"], 1.383562, places=5)

    def test_the_cache_read_override_is_what_causes_it(self):
        self.assertEqual(rates.cache_read_mult("claude-fable-5-1"), 0.025)
        self.assertEqual(rates.cache_read_mult("claude-opus-5"), 0.10)


class TestPlatformAvailability(unittest.TestCase):
    """A model must be runnable on the platform that was chosen."""

    def test_claude_code_refuses_a_non_anthropic_model(self):
        with self.assertRaises(build_model.BuildModelError) as ctx:
            build_model.resolve({"build_model": "gpt-5.4"},
                                REAL_PROFILE, "claude-code")
        self.assertIn("not available on claude-code", str(ctx.exception))

    def test_the_refusal_lists_what_is_available(self):
        with self.assertRaises(build_model.BuildModelError) as ctx:
            build_model.resolve({"build_model": "gpt-5.4"},
                                REAL_PROFILE, "claude-code")
        self.assertIn("claude-opus-5", str(ctx.exception))

    def test_github_refuses_a_model_absent_from_its_catalogue(self):
        with self.assertRaises(gh.GitHubCopilotError):
            gh.compute({"build_model": "claude-fable-5-1",
                        "interactions": 10}, 30)

    def test_claude_code_carries_only_anthropic_models(self):
        for model in rates.models_for_platform("claude-code"):
            self.assertTrue(model.startswith("claude-"),
                            "%s is not an Anthropic model" % model)

    def test_a_mix_with_one_impossible_model_is_refused(self):
        with self.assertRaises(build_model.BuildModelError):
            build_model.resolve(
                {"build_model": {"claude-opus-5": 0.5, "gpt-5.4": 0.5}},
                REAL_PROFILE, "claude-code")


class TestBadInputIsRefused(unittest.TestCase):
    def test_negative_weight(self):
        with self.assertRaises(build_model.BuildModelError):
            build_model.resolve({"build_model": {"claude-opus-5": -1}},
                                REAL_PROFILE, "claude-code")

    def test_non_numeric_weight(self):
        with self.assertRaises(build_model.BuildModelError):
            build_model.resolve({"build_model": {"claude-opus-5": "lots"}},
                                REAL_PROFILE, "claude-code")

    def test_zero_total_weight(self):
        with self.assertRaises(build_model.BuildModelError):
            build_model.resolve({"build_model": {"claude-opus-5": 0}},
                                REAL_PROFILE, "claude-code")


class TestDisclosureFallback(unittest.TestCase):
    """A missing input is disclosed, never rejected and never guessed."""

    def test_no_model_declared_is_not_repriced(self):
        info = build_model.resolve({}, REAL_PROFILE, "claude-code")
        self.assertFalse(info["repriced"])
        self.assertEqual(info["ratio"], 1.0)
        self.assertIn("No build model was declared", info["reason"])

    def test_a_profile_without_shares_refuses_to_rescale(self):
        profile = dict(REAL_PROFILE)
        profile.pop("component_shares")
        info = build_model.resolve({"build_model": "claude-opus-5"},
                                   profile, "claude-code")
        self.assertFalse(info["repriced"])
        self.assertIn("measured cost shares", info["reason"])

    def test_a_profile_without_a_model_mix_refuses_to_rescale(self):
        profile = dict(REAL_PROFILE)
        profile.pop("model_mix")
        info = build_model.resolve({"build_model": "claude-opus-5"},
                                   profile, "claude-code")
        self.assertFalse(info["repriced"])
        self.assertIn("which models produced", info["reason"])

    def test_the_cost_is_untouched_on_every_fallback(self):
        profile = dict(REAL_PROFILE)
        profile.pop("component_shares")
        info = build_model.resolve({"build_model": "claude-opus-5"},
                                   profile, "claude-code")
        self.assertEqual(info["cost_per_turn"],
                         REAL_PROFILE["cost_per_main_turn"])


class TestGitHubModelRates(unittest.TestCase):
    def test_a_declared_model_supplies_its_published_rate(self):
        out = gh.compute({"build_model": "claude-opus-5",
                          "interactions": 1000}, 30)
        self.assertIn("published GitHub rate", out["model_rate_source"])

    def test_an_explicit_rate_overrides_the_table(self):
        out = gh.compute({"build_model": "claude-opus-5",
                          "dollars_per_1m_input": 99.0,
                          "dollars_per_1m_output": 99.0,
                          "interactions": 1000}, 30)
        self.assertIn("overriding", out["model_rate_source"])

    def test_the_table_cross_checks_against_anthropic_list_price(self):
        """Corroboration is why this table was safe to ship."""
        for model in ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5",
                      "claude-sonnet-4-5"):
            self.assertEqual(rates.GITHUB_MODEL_RATES[model],
                             rates.ANTHROPIC_RATES[model],
                             "%s disagrees with Anthropic list price" % model)

    def test_legacy_mode_does_not_claim_a_sourced_multiplier(self):
        out = gh.compute({"build_model": "gpt-5.4",
                          "billing_mode": "premium-requests",
                          "model_multiplier": 1.0, "interactions": 10}, 30)
        self.assertIn("user-declared", out["model_rate_source"])
        self.assertNotIn("model_rates_verified", out)

    def test_the_rate_table_is_staleness_tracked(self):
        labels = [row[0] for row in rates._TABLES]
        self.assertIn("GitHub per-model token rates", labels)


class TestGitHubModelBlending(unittest.TestCase):
    """A team rarely builds on one model, so GitHub rates blend by share."""

    MIX = {"gpt-5.5": 0.25, "gpt-5.4": 0.50, "gpt-5-mini": 0.25}

    def test_blended_rates_are_the_weighted_published_rates(self):
        rin, rout = rates.blended_github_rates(self.MIX)
        self.assertAlmostEqual(
            rin, 0.25 * 5.00 + 0.50 * 2.50 + 0.25 * 0.25, places=6)
        self.assertAlmostEqual(
            rout, 0.25 * 30.00 + 0.50 * 15.00 + 0.25 * 2.00, places=6)

    def test_a_single_model_blend_is_that_model(self):
        self.assertEqual(rates.blended_github_rates({"gpt-5.5": 1.0}),
                         rates.GITHUB_MODEL_RATES["gpt-5.5"])

    def test_weights_need_not_sum_to_one(self):
        a = rates.blended_github_rates({"gpt-5.5": 1, "gpt-5.4": 1})
        b = rates.blended_github_rates({"gpt-5.5": 0.5, "gpt-5.4": 0.5})
        self.assertEqual(a, b)

    def test_a_blend_is_priced_between_its_members(self):
        rin, _ = rates.blended_github_rates(self.MIX)
        self.assertLess(rin, rates.GITHUB_MODEL_RATES["gpt-5.5"][0])
        self.assertGreater(rin, rates.GITHUB_MODEL_RATES["gpt-5-mini"][0])

    def test_the_report_names_every_model_in_the_blend(self):
        out = gh.compute({"build_model": dict(self.MIX),
                          "interactions": 1000}, 30)
        for model in self.MIX:
            self.assertIn(model, out["build_model"])
        self.assertIn("blended across 3 models", out["model_rate_source"])

    def test_a_blend_containing_an_unavailable_model_is_refused(self):
        with self.assertRaises(gh.GitHubCopilotError):
            gh.compute({"build_model": {"gpt-5.5": 0.5,
                                        "claude-fable-5-1": 0.5},
                        "interactions": 10}, 30)

    def test_every_gpt_rate_came_from_the_published_table(self):
        """No rate is invented to round out the catalogue."""
        for model in ("gpt-5-mini", "gpt-5.3-codex", "gpt-5.4-nano",
                      "gpt-5.4-mini", "gpt-5.4", "gpt-5.5"):
            self.assertIn(model, rates.GITHUB_MODEL_RATES)
            rin, rout = rates.GITHUB_MODEL_RATES[model]
            self.assertGreater(rin, 0)
            self.assertGreater(rout, rin, "output should cost more than input")


class TestItReachesTheEstimate(unittest.TestCase):
    def test_a_repriced_model_moves_the_build_total(self):
        cheap = dict(manifest(), build_model="claude-haiku-4-5")
        dear = dict(manifest(), build_model="claude-opus-5")
        self.assertLess(estimate.compute(cheap, REPRICEABLE)["base"],
                        estimate.compute(dear, REPRICEABLE)["base"])

    def test_the_calibration_mix_leaves_the_total_unchanged(self):
        plain = estimate.compute(manifest(), REPRICEABLE)["base"]
        declared = estimate.compute(
            dict(manifest(), build_model=dict(CAL_MIX)), REPRICEABLE)["base"]
        self.assertEqual(plain, declared)

    def test_the_result_records_the_decision(self):
        result = estimate.compute_plan(
            dict(manifest(), build_model="claude-opus-5"), REPRICEABLE)
        self.assertIn("build_model", result)
        self.assertTrue(result["build_model"]["repriced"])


class TestTheReportSaysSo(unittest.TestCase):
    def _md(self, **overrides):
        result = estimate.compute_plan(
            dict(manifest(), **overrides), REPRICEABLE)
        return rr.build_markdown(result), result

    def test_the_section_is_present(self):
        md, _ = self._md(build_model="claude-opus-5")
        self.assertIn("Which model builds it", md)

    def test_the_key_inputs_name_the_model(self):
        md, _ = self._md(build_model="claude-opus-5")
        self.assertIn("**Built by** (model)", md)

    def test_the_turn_count_limit_is_always_stated(self):
        md, _ = self._md(build_model="claude-opus-5")
        self.assertIn("more turns", md)
        self.assertIn("does not capture", md.lower())

    def test_not_repricing_is_stated_plainly(self):
        md, _ = self._md()
        self.assertIn("Not repriced", md)

    def test_a_repriced_report_still_traces_every_figure(self):
        md, result = self._md(build_model="claude-opus-5")
        self.assertEqual(assumptions.validate(md, result), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
