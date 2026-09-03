#!/usr/bin/env python3
"""Version gate: fail closed when stale, fail open when unverifiable.

Author: Dewain Robinson

No test makes a network call -- the opener is stubbed.
"""

__author__ = "Dewain Robinson"

import io
import json
import os
import shutil
import tempfile
import unittest

import _fixtures  # noqa: F401
import version_check as vc  # noqa: E402


def opener_returning(payload):
    def _open(url, timeout=None):
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return io.BytesIO(text.encode("utf-8"))
    return _open


def opener_raising(exc):
    def _open(url, timeout=None):
        raise exc
    return _open


def marketplace(version):
    return {"name": "agentdude-samples",
            "plugins": [{"name": "rfp-response", "version": "1.0.0"},
                        {"name": "build-work-estimator", "version": version}]}


class TestParseVersion(unittest.TestCase):
    def test_ordering(self):
        self.assertGreater(vc.parse_version("1.2.0"), vc.parse_version("1.1.9"))
        self.assertGreater(vc.parse_version("2.0.0"), vc.parse_version("1.99.99"))
        self.assertEqual(vc.parse_version("1.0"), vc.parse_version("1.0.0"))

    def test_junk_sorts_low(self):
        self.assertEqual(vc.parse_version(""), (0, 0, 0))
        self.assertEqual(vc.parse_version(None), (0, 0, 0))
        self.assertEqual(vc.parse_version("1.0.0-beta"), (1, 0, 0))


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.plugin_json = os.path.join(self.dir, "plugin.json")
        with open(self.plugin_json, "w") as fh:
            json.dump({"name": "build-work-estimator", "version": "1.0.0"}, fh)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _check(self, opener):
        return vc.check(plugin_json_path=self.plugin_json, opener=opener)

    def test_current_is_silent_and_exits_zero(self):
        result = self._check(opener_returning(marketplace("1.0.0")))
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["exit_code"], vc.OK)
        self.assertEqual(vc.render(result), "")

    def test_local_ahead_is_treated_as_current(self):
        result = self._check(opener_returning(marketplace("0.9.0")))
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["exit_code"], vc.OK)

    def test_stale_fails_closed_with_instructions(self):
        result = self._check(opener_returning(marketplace("1.1.0")))
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["exit_code"], vc.STALE)
        message = vc.render(result)
        self.assertIn("STOP", message)
        self.assertIn("Do not continue", message)
        self.assertIn("copilot plugin install build-work-estimator", message)

    def test_network_failure_fails_open(self):
        result = self._check(opener_raising(IOError("no route to host")))
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["exit_code"], vc.OK)
        self.assertIn("Could not verify", vc.render(result))

    def test_malformed_json_fails_open(self):
        result = self._check(opener_returning("{not json"))
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["exit_code"], vc.OK)

    def test_plugin_absent_from_marketplace_fails_open_not_current(self):
        payload = {"plugins": [{"name": "rfp-response", "version": "1.0.0"}]}
        result = self._check(opener_returning(payload))
        self.assertEqual(result["status"], "unverified")
        self.assertIn("not listed", result["reason"])

    def test_unreadable_local_plugin_json_fails_open(self):
        result = vc.check(plugin_json_path=os.path.join(self.dir, "missing.json"),
                          opener=opener_returning(marketplace("1.0.0")))
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["exit_code"], vc.OK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
