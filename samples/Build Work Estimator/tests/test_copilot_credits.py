#!/usr/bin/env python3
"""Build-time Copilot Credits: rates, harness behaviour, scope boundary.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import unittest

import _fixtures  # noqa: F401
import copilot_credits as cc  # noqa: E402
import rates  # noqa: E402

BUILD = {
    "harness": "github-copilot",
    "tier": "standard",
    "authoring_turns": 100,
    "tokens_per_turn": 4000,
    "test_runs": 20,
    "interactions_per_test_run": 5,
    "interaction_type": "generative_answer",
    "eval_runs": 10,
    "eval_tokens_per_run": 3000,
}


class TestPublishedRates(unittest.TestCase):
    def test_feature_rates_match_microsoft_table(self):
        self.assertEqual(rates.feature_credits("classic_answer"), 1)
        self.assertEqual(rates.feature_credits("generative_answer"), 2)
        self.assertEqual(rates.feature_credits("agent_action"), 5)
        self.assertEqual(rates.feature_credits("graph_grounding"), 10)
        self.assertEqual(rates.feature_credits("agent_flow_per_100"), 13)
        self.assertEqual(rates.feature_credits("content_processing_per_page"), 8)

    def test_token_tiers(self):
        self.assertEqual(rates.CC_TOKEN_TIERS["basic"], 0.1)
        self.assertEqual(rates.CC_TOKEN_TIERS["standard"], 1.5)
        self.assertEqual(rates.CC_TOKEN_TIERS["premium"], 10.0)

    def test_dollar_per_credit(self):
        self.assertEqual(rates.DOLLARS_PER_CREDIT, 0.01)

    def test_derived_dollars_per_million_tokens(self):
        self.assertAlmostEqual(rates.dollars_per_million_tokens("basic"), 1.0, 6)
        self.assertAlmostEqual(rates.dollars_per_million_tokens("standard"), 15.0, 6)
        self.assertAlmostEqual(rates.dollars_per_million_tokens("premium"), 100.0, 6)

    def test_premium_tier_dwarfs_opus_input_pricing(self):
        opus_in = rates.ANTHROPIC_RATES["claude-opus-5"][0]
        self.assertAlmostEqual(
            rates.dollars_per_million_tokens("premium") / opus_in, 20.0, 6)

    def test_credits_for_tokens(self):
        self.assertAlmostEqual(rates.credits_for_tokens(1000, "standard"), 1.5, 6)
        self.assertAlmostEqual(rates.credits_for_tokens(50000, "premium"), 500.0, 6)


class TestScopeBoundary(unittest.TestCase):
    def test_runtime_rates_exist_but_are_not_billable_features(self):
        self.assertIn("voice_genai_per_min", rates.CC_RUNTIME_ONLY)
        self.assertNotIn("voice_genai_per_min", rates.CC_FEATURES)
        self.assertEqual(rates.CC_RUNTIME_ONLY["capacity_pack_credits"], 25000)

    def test_runtime_rate_cannot_be_priced_as_a_build_feature(self):
        with self.assertRaises(ValueError):
            rates.feature_credits("voice_genai_per_min")

    def test_result_names_what_it_excludes(self):
        result = cc.compute(BUILD, 25)
        joined = " ".join(result["excluded"]).lower()
        for term in ("capacity pack", "voice", "licence", "end user"):
            self.assertIn(term.split()[0], joined)
        self.assertIn("copilot-studio-estimator", result["runtime_estimator"])

    def test_no_capacity_or_burn_keys_in_output(self):
        result = cc.compute(BUILD, 25)
        for key in result:
            for banned in ("pack", "monthly", "burn", "overage"):
                self.assertNotIn(banned, key.lower())


class TestHarness(unittest.TestCase):
    def test_standard_harness_bills_near_zero_during_build(self):
        config = dict(BUILD)
        config["harness"] = "standard"
        result = cc.compute(config, 25)
        self.assertFalse(result["bills_during_build"])
        self.assertEqual(result["total_credits"], 0.0)
        self.assertIn("after publish", result["harness_note"])

    def test_agent_flow_test_run_exemption_is_recorded(self):
        self.assertTrue(rates.AGENT_FLOW_TEST_RUNS_EXEMPT)

    def test_github_copilot_harness_bills_from_build_start(self):
        result = cc.compute(BUILD, 0)
        self.assertTrue(result["bills_during_build"])
        self.assertGreater(result["total_credits"], 0)
        self.assertIn("moment you start building", result["harness_note"])

    def test_none_harness_is_not_billed(self):
        config = dict(BUILD)
        config["harness"] = "none"
        self.assertEqual(cc.compute(config, 0)["total_credits"], 0.0)

    def test_unknown_harness_rejected(self):
        config = dict(BUILD)
        config["harness"] = "quantum"
        with self.assertRaises(cc.CreditError):
            cc.compute(config, 0)


class TestMath(unittest.TestCase):
    def test_authoring_tokens_priced_at_tier(self):
        config = dict(BUILD)
        config.update({"test_runs": 0, "eval_runs": 0})
        result = cc.compute(config, 0)
        expected = 100 * 4000 / 1000.0 * 1.5
        self.assertAlmostEqual(result["total_credits"], expected, 2)

    def test_test_iterations_charge_feature_rate_plus_tokens(self):
        config = dict(BUILD)
        config.update({"authoring_turns": 0, "eval_runs": 0})
        result = cc.compute(config, 0)
        interactions = 20 * 5
        expected = interactions * 2 + interactions * 4000 / 1000.0 * 1.5
        self.assertAlmostEqual(result["total_credits"], expected, 2)

    def test_reasoning_forces_premium_and_reports_surcharge(self):
        plain = cc.compute(BUILD, 0)
        config = dict(BUILD)
        config["reasoning_model"] = True
        reasoning = cc.compute(config, 0)
        self.assertEqual(reasoning["effective_tier"], "premium")
        self.assertEqual(reasoning["tier"], "standard")
        self.assertGreater(reasoning["total_credits"], plain["total_credits"])
        self.assertGreater(reasoning["reasoning_surcharge_credits"], 0)
        self.assertAlmostEqual(
            reasoning["total_credits"] - reasoning["reasoning_surcharge_credits"],
            plain["total_credits"], places=1)

    def test_reserve_applies_to_credits(self):
        result = cc.compute(BUILD, 25)
        self.assertAlmostEqual(
            result["budget_credits"], result["total_credits"] * 1.25, 2)
        self.assertAlmostEqual(
            result["budget_dollars"],
            round(result["budget_credits"] * 0.01, 2), 2)

    def test_dollars_track_credits(self):
        result = cc.compute(BUILD, 0)
        self.assertAlmostEqual(
            result["total_dollars"], round(result["total_credits"] * 0.01, 2), 2)

    def test_bad_tier_rejected(self):
        config = dict(BUILD)
        config["tier"] = "deluxe"
        with self.assertRaises(cc.CreditError):
            cc.compute(config, 0)


class TestRendering(unittest.TestCase):
    def test_markdown_states_build_not_run(self):
        md = cc.render_markdown(cc.compute(BUILD, 25))
        self.assertIn("consumed **building**", md)
        self.assertIn("agent usage estimator", md)
        self.assertIn("Not included", md)

    def test_zero_credit_result_explains_itself(self):
        config = dict(BUILD)
        config["harness"] = "standard"
        md = cc.render_markdown(cc.compute(config, 25))
        self.assertIn("correct result, not", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
