#!/usr/bin/env python3
"""Build stack is decided by what you build WITH, not what you build FOR.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import unittest

import _fixtures  # noqa: F401
import estimate  # noqa: E402
import github_copilot as gh  # noqa: E402
import rates  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402


class TestStackSelection(unittest.TestCase):
    def test_three_stacks_with_distinct_currencies(self):
        currencies = set(s["currency"] for s in rates.BUILD_STACKS.values())
        self.assertEqual(len(currencies), 3)
        self.assertIn("USD (tokens)", currencies)
        self.assertIn("Copilot Credits", currencies)
        self.assertIn("GitHub AI Credits", currencies)

    def test_github_and_copilot_studio_credits_are_separate_meters(self):
        # Same rate, different currencies. Conflating them is the trap.
        self.assertEqual(rates.DOLLARS_PER_CREDIT,
                         rates.DOLLARS_PER_GITHUB_AI_CREDIT)
        self.assertNotEqual(
            rates.BUILD_STACKS["copilot-studio"]["currency"],
            rates.BUILD_STACKS["github-copilot"]["currency"])
        self.assertIn("not GitHub AI Credits",
                      rates.BUILD_STACKS["copilot-studio"]["note"])

    def test_build_stack_is_required(self):
        m = manifest()
        del m["build_stack"]
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute(m, PROFILE)
        self.assertIn("build_stack is required", str(ctx.exception))

    def test_legacy_microsoft_key_is_rejected_with_guidance(self):
        m = manifest()
        del m["build_stack"]
        m["microsoft"] = True
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute(m, PROFILE)
        message = str(ctx.exception)
        self.assertIn("no longer used", message)
        self.assertIn("build_stack", message)
        self.assertIn("claude-code", message)

    def test_unknown_stack_rejected(self):
        with self.assertRaises(estimate.EstimateError):
            estimate.compute(manifest(build_stack="cursor"), PROFILE)

    def test_claude_code_building_microsoft_workload_bills_in_tokens(self):
        # The decisive case: target is Microsoft, stack is Claude Code.
        m = manifest(build_stack="claude-code")
        m["project"] = "Copilot Studio agent, built in Claude Code"
        result = estimate.compute(m, PROFILE)
        self.assertEqual(result["stack_currency"], "USD (tokens)")
        self.assertNotIn("stack_detail", result)
        self.assertGreater(result["base"], 0)

    def test_copilot_studio_stack_produces_credits_not_dollars_per_turn(self):
        m = manifest(build_stack="copilot-studio")
        m["copilot_studio"] = {"harness": "github-copilot", "tier": "standard",
                               "authoring_turns": 100}
        result = estimate.compute_stack(m, PROFILE)
        self.assertEqual(result["stack_currency"], "Copilot Credits")
        self.assertIn("stack_detail", result)
        self.assertNotIn("cost_per_main_turn", result)

    def test_github_copilot_stack_routes_to_its_own_pricer(self):
        m = manifest(build_stack="github-copilot")
        m["github_copilot"] = {"billing_mode": "premium-requests",
                               "interactions": 400, "model_multiplier": 1.0}
        result = estimate.compute_stack(m, PROFILE)
        self.assertEqual(result["stack_currency"], "GitHub AI Credits")
        self.assertEqual(result["stack_detail"]["unit"], "premium request")


class TestGitHubCopilot(unittest.TestCase):
    def test_ai_credits_requires_published_rates(self):
        with self.assertRaises(gh.GitHubCopilotError) as ctx:
            gh.compute({"billing_mode": "ai-credits", "interactions": 100}, 25)
        self.assertIn("not hardcoded", str(ctx.exception))

    def test_ai_credits_math(self):
        result = gh.compute({
            "billing_mode": "ai-credits", "interactions": 100,
            "tokens_per_interaction": 10000, "output_share": 0.2,
            "dollars_per_1m_input": 5.0, "dollars_per_1m_output": 25.0,
        }, 0)
        # 1,000,000 tokens: 800k in @ $5/M, 200k out @ $25/M = $4 + $5 = $9
        self.assertAlmostEqual(result["total_dollars"], 9.0, places=2)
        self.assertAlmostEqual(result["total_units"], 900.0, places=0)

    def test_auto_discount_reduces_credits(self):
        base = dict(billing_mode="ai-credits", interactions=100,
                    tokens_per_interaction=10000, output_share=0.2,
                    dollars_per_1m_input=5.0, dollars_per_1m_output=25.0)
        full = gh.compute(base, 0)
        cfg = dict(base); cfg["auto_discount"] = 0.5
        discounted = gh.compute(cfg, 0)
        self.assertAlmostEqual(
            discounted["total_units"], full["total_units"] / 2, places=0)

    def test_premium_requests_apply_model_multiplier(self):
        result = gh.compute({"billing_mode": "premium-requests",
                             "interactions": 200, "model_multiplier": 3.0}, 0)
        self.assertEqual(result["total_units"], 600.0)

    def test_premium_requests_flag_allowance_overrun(self):
        result = gh.compute({"billing_mode": "premium-requests",
                             "interactions": 400, "model_multiplier": 2.0,
                             "monthly_allowance": 300}, 0)
        self.assertTrue(result["exceeds_allowance"])

    def test_completions_are_unmetered_and_said_so(self):
        result = gh.compute({"billing_mode": "premium-requests",
                             "interactions": 10}, 0)
        joined = " ".join(result["unmetered"]).lower()
        self.assertIn("completions", joined)
        md = gh.render_markdown(result)
        self.assertIn("Not metered", md)
        self.assertIn("unlimited on paid plans", md)

    def test_reserve_applies_to_units(self):
        result = gh.compute({"billing_mode": "premium-requests",
                             "interactions": 100, "model_multiplier": 1.0}, 25)
        self.assertAlmostEqual(result["budget_units"], 125.0, places=0)

    def test_render_states_it_is_a_different_meter(self):
        md = gh.render_markdown(gh.compute(
            {"billing_mode": "premium-requests", "interactions": 50}, 10))
        self.assertIn("different meter from Copilot Studio", md)

    def test_bad_billing_mode_rejected(self):
        with self.assertRaises(gh.GitHubCopilotError):
            gh.compute({"billing_mode": "vibes", "interactions": 1}, 0)


class TestNoTokenDenomination(unittest.TestCase):
    """Microsoft products bill in credits. No headline may say 'tokens'."""

    def setUp(self):
        import render_report as rr
        m = manifest(build_stack="copilot-studio", reserve_percent=30)
        m["copilot_studio"] = {"harness": "github-copilot", "tier": "standard",
                               "reasoning_model": True, "authoring_turns": 160,
                               "test_runs": 45, "eval_runs": 30}
        self.md = rr.build_markdown(estimate.compute_stack(m, PROFILE))

    def test_no_heading_is_denominated_in_tokens(self):
        for line in self.md.splitlines():
            if line.startswith("#"):
                self.assertNotIn("token", line.lower(),
                                 "heading denominated in tokens: %r" % line)

    def test_no_table_row_label_is_denominated_in_tokens(self):
        for line in self.md.splitlines():
            if not line.startswith("|"):
                continue
            label = line.split("|")[1].lower() if "|" in line else ""
            self.assertNotIn("token", label,
                             "row label denominated in tokens: %r" % line)

    def test_totals_are_credits(self):
        self.assertIn("Total build credits", self.md)
        self.assertIn("Copilot Credits", self.md)

    def test_claude_dollar_per_turn_never_appears(self):
        self.assertNotIn("Cost per agent turn", self.md)
        self.assertNotIn("Calibration basis", self.md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
