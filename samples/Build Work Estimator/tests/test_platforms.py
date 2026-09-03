#!/usr/bin/env python3
"""Two axes: what builds it, and what it runs on. Different questions.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import unittest

import _fixtures  # noqa: F401
import estimate  # noqa: E402
import github_copilot as gh  # noqa: E402
import rates  # noqa: E402
import render_report as rr  # noqa: E402
import target_platform as tp  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402


class TestAxesAreSeparate(unittest.TestCase):
    def test_only_coding_agents_are_build_platforms(self):
        self.assertEqual(sorted(rates.BUILD_PLATFORMS),
                         ["claude-code", "github-copilot"])

    def test_copilot_studio_is_a_target_not_a_build_platform(self):
        self.assertIn("copilot-studio", rates.TARGET_PLATFORMS)
        self.assertNotIn("copilot-studio", rates.BUILD_PLATFORMS)

    def test_target_options_cover_the_asked_set(self):
        self.assertEqual(sorted(rates.TARGET_PLATFORMS),
                         ["ai-recommend", "azure", "both", "copilot-studio"])

    def test_both_axes_required(self):
        for missing in ("build_platform", "target_platform"):
            m = manifest()
            del m[missing]
            with self.assertRaises(estimate.EstimateError) as ctx:
                estimate.compute_plan(m, PROFILE)
            self.assertIn("%s is required" % missing, str(ctx.exception))

    def test_legacy_build_stack_rejected_with_guidance(self):
        m = manifest()
        del m["build_platform"]
        m["build_stack"] = "copilot-studio"
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute_plan(m, PROFILE)
        message = str(ctx.exception)
        self.assertIn("replaced by two separate keys", message)
        self.assertIn("never a build platform", message)

    def test_ai_recommend_must_be_resolved_before_estimating(self):
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute_plan(manifest(target_platform="ai-recommend"),
                                  PROFILE)
        message = str(ctx.exception)
        self.assertIn("will not silently pick one", message)

    def test_unknown_values_rejected(self):
        with self.assertRaises(estimate.EstimateError):
            estimate.compute_plan(manifest(build_platform="copilot-studio"),
                                  PROFILE)
        with self.assertRaises(estimate.EstimateError):
            estimate.compute_plan(manifest(target_platform="salesforce"),
                                  PROFILE)


class TestBothMetersAreAdditive(unittest.TestCase):
    def test_plan_carries_build_and_target(self):
        result = estimate.compute_plan(manifest(), PROFILE)
        self.assertIsNotNone(result["build"])
        self.assertEqual(len(result["targets"]), 1)
        self.assertGreater(result["build"]["base"], 0)

    def test_both_target_expands_to_two_meters(self):
        m = manifest(target_platform="both")
        m["target"] = {"harness": "github-copilot", "eval_test_cases": 5,
                       "azure_build_usd": 120.0}
        result = estimate.compute_plan(m, PROFILE)
        self.assertEqual(sorted(t["target"] for t in result["targets"]),
                         ["azure", "copilot-studio"])

    def test_github_copilot_build_platform_routes_to_its_pricer(self):
        m = manifest(build_platform="github-copilot")
        m["github_copilot"] = {"billing_mode": "premium-requests",
                               "interactions": 500}
        result = estimate.compute_plan(m, PROFILE)
        self.assertIsNone(result["build"])
        self.assertEqual(result["build_detail"]["unit"], "premium request")
        self.assertEqual(result["build_currency"], "GitHub AI Credits")


class TestTargetHarness(unittest.TestCase):
    """The harness decides whether any build/test work bills at all."""

    def test_harness_is_required(self):
        m = manifest()
        m["target"] = {"eval_test_cases": 10}
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute_plan(m, PROFILE)
        message = str(ctx.exception)
        self.assertIn("target harness is required", message)
        self.assertIn("not guessed", message)

    def test_unknown_harness_rejected(self):
        with self.assertRaises(tp.TargetPlatformError):
            tp.compute({"harness": "turbo"}, 0)

    def test_standard_harness_does_not_bill_preview_or_evaluation(self):
        out = tp.compute({"harness": "standard", "eval_test_cases": 50,
                          "eval_repeats": 3, "eval_cycles": 3,
                          "interactive_test_hours": 20}, 0)
        self.assertFalse(out["bills_during_build"])
        self.assertEqual(out["total_credits"], 0.0)
        self.assertGreater(out["unbilled_credits"], 0,
                           "the counterfactual should still be computed")

    def test_github_copilot_harness_bills_all_of_it(self):
        out = tp.compute({"harness": "github-copilot", "eval_test_cases": 50,
                          "eval_repeats": 3, "eval_cycles": 3,
                          "interactive_test_hours": 20}, 0)
        self.assertTrue(out["bills_during_build"])
        self.assertGreater(out["total_credits"], 0)

    def test_agent_flow_test_runs_are_exempt_on_the_standard_harness(self):
        """Microsoft documents the exemption explicitly.

        "Testing an agent flow in the flow designer or from the agent's test
        chat doesn't consume capacity for agent flow actions." Billing them
        anyway over-charged every standard-harness build estimate.
        """
        out = tp.compute({"harness": "standard", "agent_flow_actions": 500,
                          "eval_cycles": 1}, 0)
        self.assertEqual(out["total_credits"], 0.0)
        self.assertTrue(out["agent_flow_test_runs_exempt"])

    def test_agent_flow_runs_do_bill_on_the_github_copilot_harness(self):
        out = tp.compute({"harness": "github-copilot",
                          "agent_flow_actions": 500, "eval_cycles": 1}, 0)
        self.assertAlmostEqual(out["total_credits"], 500 / 100.0 * 13, 2)


class TestEvaluationLoop(unittest.TestCase):
    def test_eval_runs_scale_with_cases_repeats_and_cycles(self):
        out = tp.compute({"harness": "github-copilot", "eval_test_cases": 10,
                          "eval_repeats": 3, "eval_cycles": 4}, 0)
        self.assertEqual(out["eval_runs"], 120)

    def test_remediation_scales_the_build_side(self):
        one = manifest()
        one["target"] = {"harness": "standard", "eval_cycles": 1}
        four = manifest()
        four["target"] = {"harness": "standard", "eval_cycles": 4}
        a = estimate.compute_plan(one, PROFILE)
        b = estimate.compute_plan(four, PROFILE)
        expected = 1 + 3 * estimate.REMEDIATION_SHARE
        self.assertAlmostEqual(
            b["build"]["base"] / a["build"]["base"], expected, places=2)

    def test_velocity_cap_produces_minimum_elapsed_days(self):
        out = tp.compute({"harness": "github-copilot", "eval_test_cases": 40,
                          "eval_repeats": 3, "eval_cycles": 4}, 0)
        # 120 runs per cycle at 20/day = 6 days per cycle, 4 cycles = 24.
        self.assertEqual(out["min_elapsed_days"], 24)
        self.assertEqual(out["eval_cap_per_day"],
                         rates.MAX_EVALUATIONS_PER_NODE_PER_DAY)

    def test_interactive_hours_size_the_test_volume(self):
        out = tp.compute({"harness": "github-copilot",
                          "interactive_test_hours": 10,
                          "interactions_per_hour": 30}, 0)
        self.assertEqual(out["interactive_interactions"], 300)

    def test_human_hours_are_not_priced_as_labour(self):
        out = tp.compute({"harness": "github-copilot",
                          "interactive_test_hours": 10}, 0)
        md = tp.render_markdown(out)
        self.assertIn("not** estimated as labour", md)
        self.assertIn("dependency, not a cost line", md)

    def test_reserve_applies_to_target_credits(self):
        out = tp.compute({"harness": "github-copilot", "eval_test_cases": 20}, 25)
        self.assertAlmostEqual(out["budget_credits"],
                               out["total_credits"] * 1.25, places=1)


class TestCurrencySeparation(unittest.TestCase):
    def test_github_and_copilot_studio_credits_stay_separate(self):
        self.assertEqual(rates.DOLLARS_PER_CREDIT,
                         rates.DOLLARS_PER_GITHUB_AI_CREDIT)
        self.assertNotEqual(
            rates.BUILD_PLATFORMS["github-copilot"]["currency"],
            rates.TARGET_PLATFORMS["copilot-studio"]["currency"])

    def test_target_report_is_denominated_in_credits(self):
        m = manifest()
        m["target"] = {"harness": "github-copilot", "eval_test_cases": 20,
                       "interactive_test_hours": 5}
        md = tp.render_markdown(estimate.compute_plan(m, PROFILE)["targets"][0])
        for line in md.splitlines():
            if line.startswith("#"):
                self.assertNotIn("token", line.lower())
            if line.startswith("|"):
                label = line.split("|")[1].lower()
                self.assertNotIn("token", label)


class TestGitHubCopilot(unittest.TestCase):
    def test_ai_credits_requires_published_rates(self):
        with self.assertRaises(gh.GitHubCopilotError) as ctx:
            gh.compute({"billing_mode": "ai-credits", "interactions": 100}, 25)
        self.assertIn("not hardcoded", str(ctx.exception))

    def test_ai_credits_math(self):
        out = gh.compute({
            "billing_mode": "ai-credits", "interactions": 100,
            "tokens_per_interaction": 10000, "output_share": 0.2,
            "dollars_per_1m_input": 5.0, "dollars_per_1m_output": 25.0}, 0)
        self.assertAlmostEqual(out["total_dollars"], 9.0, places=2)
        self.assertAlmostEqual(out["total_units"], 900.0, places=0)

    def test_premium_requests_apply_multiplier_and_flag_overrun(self):
        out = gh.compute({"billing_mode": "premium-requests",
                          "interactions": 400, "model_multiplier": 2.0,
                          "monthly_allowance": 300}, 0)
        self.assertEqual(out["total_units"], 800.0)
        self.assertTrue(out["exceeds_allowance"])

    def test_completions_are_unmetered(self):
        out = gh.compute({"billing_mode": "premium-requests",
                          "interactions": 10}, 0)
        self.assertIn("Not metered", gh.render_markdown(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
