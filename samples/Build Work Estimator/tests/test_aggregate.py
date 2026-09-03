#!/usr/bin/env python3
"""Community baseline aggregation: medians, IQR, confidence gate, resilience.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "calibration"))

import aggregate  # noqa: E402

RECORD = """schema: 1
contributed: 2026-09
size: {size}
files: 9
unknowns: 2
brownfield: true
estimated_turns: 431
actual_turns: {actual}
ratio: {ratio}
model_tier: opus
cache_hit_rate_band: "95-100"
harness: none
"""


class TestAggregate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, **kw):
        params = {"size": "medium", "actual": 604, "ratio": 1.4}
        params.update(kw)
        with open(os.path.join(self.dir, name), "w") as fh:
            fh.write(RECORD.format(**params))

    def test_empty_dir_yields_empty_baseline(self):
        result = aggregate.aggregate(self.dir)
        self.assertEqual(result["records"], 0)
        self.assertEqual(result["buckets"], {})

    def test_missing_dir_does_not_crash(self):
        result = aggregate.aggregate(os.path.join(self.dir, "nope"))
        self.assertEqual(result["records"], 0)

    def test_median_across_records(self):
        for index, ratio in enumerate([1.0, 1.4, 2.0]):
            self._write("r%d.yaml" % index, ratio=ratio)
        result = aggregate.aggregate(self.dir)
        self.assertEqual(result["buckets"]["medium"]["n"], 3)
        self.assertAlmostEqual(
            result["buckets"]["medium"]["median_ratio"], 1.4, places=3)

    def test_confidence_gate_at_five(self):
        for index in range(4):
            self._write("a%d.yaml" % index, ratio=1.2)
        self.assertFalse(aggregate.aggregate(self.dir)["buckets"]["medium"]["confident"])
        self._write("a4.yaml", ratio=1.2)
        self.assertTrue(aggregate.aggregate(self.dir)["buckets"]["medium"]["confident"])

    def test_buckets_kept_separate(self):
        self._write("m.yaml", size="medium", ratio=1.4)
        self._write("s.yaml", size="small", ratio=0.8)
        result = aggregate.aggregate(self.dir)
        self.assertEqual(sorted(result["buckets"]), ["medium", "small"])

    def test_malformed_file_skipped_not_fatal(self):
        self._write("good.yaml", ratio=1.4)
        with open(os.path.join(self.dir, "bad.yaml"), "w") as fh:
            fh.write("this: is: not: valid: yaml: [\n")
        with open(os.path.join(self.dir, "incomplete.yaml"), "w") as fh:
            fh.write("schema: 1\nsize: medium\n")  # no ratio
        result = aggregate.aggregate(self.dir)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["skipped"], 2)

    def test_nonsense_ratio_rejected(self):
        self._write("zero.yaml", ratio=0)
        self._write("negative.yaml", ratio=-2)
        result = aggregate.aggregate(self.dir)
        self.assertEqual(result["records"], 0)
        self.assertEqual(result["skipped"], 2)

    def test_non_yaml_ignored_entirely(self):
        self._write("ok.yaml", ratio=1.4)
        with open(os.path.join(self.dir, "README.md"), "w") as fh:
            fh.write("not a record")
        result = aggregate.aggregate(self.dir)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["skipped"], 0)

    def test_note_states_self_selection_limit(self):
        note = aggregate.aggregate(self.dir)["note"].lower()
        self.assertIn("self-selected", note)
        self.assertIn("never better", note)


if __name__ == "__main__":
    unittest.main(verbosity=2)
