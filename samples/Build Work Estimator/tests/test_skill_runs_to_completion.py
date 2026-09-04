#!/usr/bin/env python3
"""The instructions that stop a session ending in "ready to execute".

Author: Dewain Robinson

A real GitHub Copilot session collected every input across three rounds of
questions and then produced nothing, answering "run it now" with "Estimate run
is ready to execute". Four defects in the instructions caused it, and this
suite pins each one so it cannot quietly return.

These check SKILL.md text rather than behaviour, which is a real limit: they
prove the instruction is present, not that a model followed it. That is worth
having anyway -- every one of these failures traced to an instruction that was
absent or wrong, not to an instruction that was ignored.
"""

__author__ = "Dewain Robinson"

import os
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
SKILL = os.path.join(SAMPLE, "skill", "build-work-estimator", "SKILL.md")


def skill_text():
    with open(SKILL) as fh:
        return fh.read()


class TestDoneMeansTheReportExists(unittest.TestCase):
    """The failure that wasted the whole session."""

    def test_the_skill_says_announcing_is_not_running(self):
        t = skill_text()
        self.assertIn("Announcing that you are ready to run the estimate is "
                      "not running it", t)

    def test_the_failure_phrases_are_named_explicitly(self):
        """Naming the exact phrases beats describing the failure abstractly."""
        t = skill_text()
        for phrase in ("Ready to execute", "settings locked"):
            self.assertIn(phrase, t)

    def test_completion_is_defined_as_files_produced(self):
        t = skill_text()
        self.assertIn("Done means the report exists", t)
        self.assertIn("an estimate is a file", t)

    def test_it_says_run_in_the_same_turn(self):
        t = skill_text()
        self.assertIn("same turn you finish collecting them", t)

    def test_a_collecting_conversation_with_no_file_is_called_a_failure(self):
        t = skill_text()
        self.assertIn("produces no file has failed", t)


class TestTheBreakdownIsNotOptional(unittest.TestCase):
    """The false comment that hid the most important input."""

    def test_github_copilot_is_not_told_to_skip_items(self):
        t = skill_text()
        self.assertNotIn("github-copilot uses this instead of items", t,
                         "this claim is false -- estimate.py derives "
                         "interactions FROM items -- and it is why a real "
                         "session never asked for the work breakdown")

    def test_the_skill_says_both_platforms_use_items(self):
        t = skill_text()
        self.assertIn("ALSO uses items", t)
        self.assertIn("DERIVED from the same breakdown", t)

    def test_interactions_are_documented_as_derived(self):
        """Proving the doc matches the code it describes."""
        import estimate  # noqa: F401
        source = open(os.path.join(
            SAMPLE, "skill", "build-work-estimator", "scripts",
            "estimate.py")).read()
        self.assertIn('gh_cfg["interactions"] = sizing["total_turns"]', source,
                      "if this derivation goes away, the SKILL.md claim that "
                      "items drive a GitHub build stops being true")


class TestItReadsTheSpecification(unittest.TestCase):
    def test_the_skill_says_to_open_the_specification(self):
        t = skill_text()
        self.assertIn("open it before asking them anything", t)

    def test_it_drafts_a_breakdown_from_the_specification(self):
        t = skill_text()
        self.assertIn("draft the **work breakdown**", t)

    def test_the_draft_must_be_confirmed_not_assumed(self):
        t = skill_text()
        self.assertIn("ask the user to correct it", t)
        self.assertIn("not a measurement", t)

    def test_it_is_told_to_include_operating_work(self):
        """The omission class the researcher gate actually found."""
        t = skill_text()
        self.assertIn("recovery, load testing, key management, residency", t)


class TestItAsksOnce(unittest.TestCase):
    def test_the_skill_requires_a_single_round(self):
        t = skill_text()
        self.assertIn("ONE message", t)
        self.assertIn("not one at a time", t)

    def test_defaults_are_offered_for_what_can_be_defaulted(self):
        t = skill_text()
        self.assertIn("Offer a sensible default", t)

    def test_reserve_percent_is_never_defaulted(self):
        t = skill_text()
        self.assertIn("No default. Required, always ask.", t)

    def test_it_must_not_ask_what_the_specification_answers(self):
        t = skill_text()
        self.assertIn("Never ask for something the specification already "
                      "answers", t)


class TestItChallengesAnImplausibleRate(unittest.TestCase):
    def test_the_skill_says_to_sanity_check_a_declared_rate(self):
        t = skill_text()
        self.assertIn("Sanity-check a declared rate before you use it", t)

    def test_it_must_not_invent_a_replacement_figure(self):
        t = skill_text()
        self.assertIn("must not invent a figure to replace", t)

    def test_it_points_at_the_published_source(self):
        t = skill_text()
        self.assertIn("docs.github.com/en/copilot/get-started/plans", t)

    def test_the_stakes_are_stated(self):
        t = skill_text()
        self.assertIn("no reserve covers", t)


class TestDraftedSizesAreDisclosed(unittest.TestCase):
    """A drafted size and an authored one are different claims."""

    def setUp(self):
        import estimate
        import render_report as rr
        from test_estimate import PROFILE, manifest
        self.estimate, self.rr = estimate, rr
        self.PROFILE, self.manifest = PROFILE, manifest

    def test_absent_means_authored(self):
        result = self.estimate.compute_plan(self.manifest(), self.PROFILE)
        self.assertEqual(result["breakdown_source"], "authored")

    def test_a_drafted_breakdown_is_recorded(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        result = self.estimate.compute_plan(m, self.PROFILE)
        self.assertEqual(result["breakdown_source"], "drafted")

    def test_a_drafted_breakdown_is_visible_in_the_report(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        md = self.rr.build_markdown(
            self.estimate.compute_plan(m, self.PROFILE))
        self.assertIn("drafted from the specification", md)
        self.assertIn("weaker than an authored breakdown", md)

    def test_an_authored_breakdown_makes_no_claim(self):
        md = self.rr.build_markdown(
            self.estimate.compute_plan(self.manifest(), self.PROFILE))
        self.assertNotIn("drafted from the specification", md)

    def test_an_unknown_source_is_refused(self):
        import specification as spec_mod
        with self.assertRaises(spec_mod.SpecificationError):
            spec_mod.normalise_breakdown_source("guessed")

    def test_disclosure_changes_no_figure(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        self.assertEqual(
            self.estimate.compute_plan(self.manifest(),
                                       self.PROFILE)["totals"],
            self.estimate.compute_plan(m, self.PROFILE)["totals"],
            "how the breakdown was produced is a confidence signal, not an "
            "input to the arithmetic")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestVersionHasOneSource(unittest.TestCase):
    """Bumping the plugin must bump everything a client compares against.

    build_host_packages.py used to carry its own VERSION constant, so raising
    the plugin's version left the Cowork package manifest behind at the old
    number with nothing checking that the two agreed.
    """

    def _build_dir(self, name):
        return os.path.join(SAMPLE, "build", name)

    def test_host_packages_does_not_define_its_own_version(self):
        source = open(self._build_dir("build_host_packages.py")).read()
        self.assertNotIn('VERSION = "', source,
                         "a second version constant drifts from the first")

    def test_every_artifact_reports_the_same_version(self):
        import json
        import zipfile
        repo = os.path.abspath(os.path.join(SAMPLE, "..", ".."))

        plugin = json.load(open(os.path.join(
            repo, "plugins", "build-work-estimator", "plugin.json")))
        market = json.load(open(os.path.join(
            repo, ".github", "plugin", "marketplace.json")))
        entry = [p for p in market["plugins"]
                 if p["name"] == "build-work-estimator"][0]
        with zipfile.ZipFile(os.path.join(
                SAMPLE, "packages",
                "build-work-estimator-cowork-plugin.zip")) as z:
            cowork = json.loads(z.read("manifest.json"))["version"]

        self.assertEqual(plugin["version"], entry["version"],
                         "version_check compares these two directly")
        self.assertEqual(plugin["version"], cowork,
                         "the Cowork package must not ship a stale version")


class TestTargetIsRecommendedNotAskedCold(unittest.TestCase):
    """Copilot Studio and Azure are both Microsoft; the choice follows from
    the requirements rather than being a preference the user must hold."""

    def test_the_skill_says_not_to_ask_the_platform_cold(self):
        t = skill_text()
        self.assertIn("Do not ask this cold", t)

    def test_it_recommends_from_the_specification(self):
        t = skill_text()
        self.assertIn("read it and recommend", t)
        self.assertIn("Signal in the requirements", t)

    def test_the_harness_is_asked_as_a_preference_first(self):
        t = skill_text()
        self.assertIn("Ask this one as a preference first", t)

    def test_the_harness_offers_a_recommendation_too(self):
        t = skill_text()
        self.assertIn("If you'd rather I recommend one", t)

    def test_both_recommendations_are_on_fit_not_cost(self):
        """The tool must not steer architecture with its own number."""
        t = skill_text()
        self.assertEqual(t.count("Recommend on fit, never on cost."), 2,
                         "the rule belongs on both the platform and the "
                         "harness recommendation")
        self.assertIn("steering an architecture decision with its own number",
                      t)

    def test_harness_ai_recommend_is_refused_by_the_estimator(self):
        import target_platform as tp
        with self.assertRaises(tp.TargetPlatformError) as caught:
            tp.validate_harness("ai-recommend")
        self.assertIn("still `ai-recommend`", str(caught.exception))

    def test_the_harness_error_says_to_decide_on_fit(self):
        import target_platform as tp
        with self.assertRaises(tp.TargetPlatformError) as caught:
            tp.validate_harness("ai-recommend")
        self.assertIn("Recommend on FIT, never on cost",
                      str(caught.exception))

    def test_real_harness_values_still_validate(self):
        import target_platform as tp
        self.assertEqual(tp.validate_harness("standard"), "standard")
        self.assertEqual(tp.validate_harness("github-copilot"),
                         "github-copilot")


class TestItReportsProgress(unittest.TestCase):
    """Silence is indistinguishable from nothing happening."""

    def test_the_skill_says_to_announce_starting(self):
        t = skill_text()
        self.assertIn("Say that you have started", t)
        self.assertIn("before the first slow step", t)

    def test_it_reports_after_each_phase(self):
        t = skill_text()
        self.assertIn("One short line per phase", t)

    def test_it_says_to_surface_a_slow_or_failing_step(self):
        t = skill_text()
        self.assertIn("If something is slow, say it is slow", t)


class TestOneCommandProducesTheDeliverable(unittest.TestCase):
    """Estimating and rendering were two commands, so "run it" was a sequence
    whose second half kept not happening while the assistant narrated as
    though it had."""

    def test_estimate_can_render_in_one_invocation(self):
        import subprocess
        import tempfile
        out = os.path.join(tempfile.mkdtemp(), "e")
        scripts = os.path.join(SAMPLE, "skill", "build-work-estimator",
                               "scripts")
        proc = subprocess.run(
            [__import__("sys").executable,
             os.path.join(scripts, "estimate.py"),
             "--manifest", os.path.join(SAMPLE, "examples",
                                        "harbor-line-manifest.yaml"),
             "--profile", os.path.join(SAMPLE, "examples",
                                       "calibration-profile.json"),
             "--no-ledger", "--report", out],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out + ".md"),
                        "one command must leave a report behind")

    def test_it_prints_the_headline_so_the_run_is_visible(self):
        import subprocess
        import tempfile
        out = os.path.join(tempfile.mkdtemp(), "e")
        scripts = os.path.join(SAMPLE, "skill", "build-work-estimator",
                               "scripts")
        proc = subprocess.run(
            [__import__("sys").executable,
             os.path.join(scripts, "estimate.py"),
             "--manifest", os.path.join(SAMPLE, "examples",
                                        "harbor-line-manifest.yaml"),
             "--profile", os.path.join(SAMPLE, "examples",
                                       "calibration-profile.json"),
             "--no-ledger", "--report", out],
            capture_output=True, text=True)
        self.assertIn("Likely $", proc.stdout)
        self.assertIn("with reserve $", proc.stdout)

    def test_render_write_is_shared_not_duplicated(self):
        import render_report
        self.assertTrue(callable(getattr(render_report, "write", None)),
                        "estimate --report and the CLI must share one writer")

    def test_the_skill_prefers_the_single_command(self):
        t = skill_text()
        self.assertIn("Prefer the single command", t)


class TestItDoesNotClaimToBeRunning(unittest.TestCase):
    """The worst failure yet: asserting it was running when it was not."""

    def test_the_rule_exists(self):
        t = skill_text()
        self.assertIn("Never say you ran something you did not run", t)

    def test_a_status_claim_must_be_backed_by_output(self):
        t = skill_text()
        self.assertIn("must be backed by output you can point at", t)

    def test_it_says_nothing_runs_between_messages(self):
        t = skill_text()
        self.assertIn("nothing runs between your messages", t)

    def test_it_says_to_run_in_the_same_reply_when_caught(self):
        t = skill_text()
        self.assertIn("run it in that same reply", t)


class TestTheBreakdownIsFirstInTheReadinessList(unittest.TestCase):
    def test_items_is_named_as_a_required_input(self):
        t = skill_text()
        self.assertIn("**`items:` — the work breakdown.**", t)

    def test_the_omission_that_caused_it_is_recorded(self):
        t = skill_text()
        self.assertIn("mentioned the breakdown at all", t)


class TestInputsAreCheckedForCoherence(unittest.TestCase):
    """Every field can be individually valid while the manifest contradicts
    itself. Instructions failed at this three times; this is the code check."""

    def setUp(self):
        import estimate
        self.check = estimate.check_coherence

    def test_a_claude_plan_on_a_github_build_is_flagged(self):
        out = self.check({"build_platform": "github-copilot",
                          "licensing": {"plan": "Claude Max"}})
        self.assertTrue(any("does not pay for GitHub Copilot" in w
                            for w in out))

    def test_a_copilot_plan_on_a_claude_build_is_flagged(self):
        out = self.check({"build_platform": "claude-code",
                          "licensing": {"plan": "GitHub Copilot Business"}})
        self.assertTrue(any("does not pay for Claude Code" in w for w in out))

    def test_copilot_studio_fields_on_an_azure_target_are_flagged(self):
        out = self.check({"build_platform": "claude-code",
                          "target_platform": "azure",
                          "target": {"harness": "standard",
                                     "tier": "premium"}})
        self.assertTrue(any("no Copilot Studio in it" in w for w in out))

    def test_azure_spend_on_a_studio_only_target_is_flagged(self):
        out = self.check({"target_platform": "copilot-studio",
                          "target": {"azure_build_usd": 900}})
        self.assertTrue(any("no Azure in it" in w for w in out))

    def test_a_standard_harness_on_a_github_build_is_NOT_flagged(self):
        """Deliberate in two shipped examples, and ungroundable as unusual."""
        out = self.check({"build_platform": "github-copilot",
                          "target_platform": "both",
                          "target": {"harness": "standard"}})
        self.assertEqual(out, [],
                         "a check that fires on valid input teaches people to "
                         "ignore checks")

    def test_an_unused_github_block_is_flagged(self):
        out = self.check({"build_platform": "claude-code",
                          "github_copilot": {"billing_mode": "ai-credits"}})
        self.assertTrue(any("none of it is used" in w for w in out))

    def test_a_coherent_manifest_produces_no_noise(self):
        out = self.check({"build_platform": "github-copilot",
                          "target_platform": "both",
                          "licensing": {"plan": "GitHub Copilot Business"},
                          "target": {"harness": "github-copilot",
                                     "tier": "premium"},
                          "github_copilot": {"billing_mode": "ai-credits"}})
        self.assertEqual(out, [], "a valid manifest must not be nagged")

    def test_warnings_reach_the_report(self):
        import estimate
        import render_report as rr
        from test_estimate import PROFILE, manifest
        m = manifest()
        m["build_platform"] = "github-copilot"
        m["licensing"] = dict(m.get("licensing") or {}, plan="Claude Max")
        # A GitHub build needs a model so its rates come from the table.
        m["github_copilot"] = {"billing_mode": "ai-credits",
                               "build_model": "gpt-5.4"}
        result = estimate.compute_plan(m, PROFILE)
        self.assertTrue(result["coherence"])
        self.assertIn("Check inputs", rr.build_markdown(result))


class TestNoGuessedDefaults(unittest.TestCase):
    def test_the_harness_must_never_be_proposed(self):
        t = skill_text()
        self.assertIn("Never propose a `target.harness`", t)

    def test_the_likely_github_pairing_is_named(self):
        t = skill_text()
        self.assertIn("usually means the `github-copilot` harness", t)

    def test_example_values_must_not_be_proposed_as_drafted(self):
        t = skill_text()
        self.assertIn("Never propose a value copied from the manifest example",
                      t)
        self.assertIn("they were drafted from an example", t)

    def test_tier_is_labelled_as_a_copilot_studio_field(self):
        t = skill_text()
        self.assertIn("**Copilot Studio fields**", t)
