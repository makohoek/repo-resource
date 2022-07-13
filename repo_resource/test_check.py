#!/usr/bin/env python

# SPDX-License-Identifier: Apache-2.0
# Copyright 2022 (c) BayLibre, SAS
# Author: Mattijs Korpershoek <mkorpershoek@baylibre.com>

import json
from io import StringIO
import unittest
from pathlib import Path
import shutil
import repo

from . import check
from . import common


class TestCheck(unittest.TestCase):

    def setUp(self):
        self.aosp_platform_source = {
            'source': {
                'url': 'https://android.googlesource.com/platform'
            }
        }
        self.demo_manifests_source = {
            'source': {
                'url': 'https://github.com/makohoek/demo-manifests.git',
                'revision': 'main',
                'name': 'aosp_device_fixed.xml'
            }
        }
        self.demo_ssh_manifests_source = {
            'source': {
                'url': 'https://github.com/makohoek/demo-manifests.git',
                'revision': 'main',
                'name': 'baylibre_ssh_project.xml',
            }
        }

    def tearDown(self):
        p = common.CACHEDIR
        if p.exists():
            shutil.rmtree(p)

    def test_input_json_fails_without_source(self):
        incomplete_data = {'source': {}}
        instream = StringIO(json.dumps(incomplete_data))
        with self.assertRaises(RuntimeError):
            check.check(instream)

    def test_invalid_manifest_url(self):
        invalid_data = {
            'source': {
                'url': 'this-is-not-an-url',
            },
        }
        instream = StringIO(json.dumps(invalid_data))
        with self.assertRaises(repo.error.GitError):
            check.check(instream)

    def test_unreachable_manifest(self):
        unreachable_data = {
            'source': {
                'url':
                'https://android.googlesource.com/platform/manifest-typo'
            },
        }
        instream = StringIO(json.dumps(unreachable_data))
        with self.assertRaises(repo.error.GitError):
            check.check(instream)

    def test_unknown_revision(self):
        unknown_revision_data = self.aosp_platform_source
        unknown_revision_data['source']['revision'] = 'unknown'
        instream = StringIO(json.dumps(unknown_revision_data))
        with self.assertRaises(SystemExit):
            check.check(instream)

    def test_unknown_manifest_name(self):
        unknown_manifest_data = self.aosp_platform_source
        unknown_manifest_data['source']['revision'] = 'master'
        unknown_manifest_data['source']['name'] = 'unknown.xml'
        instream = StringIO(json.dumps(unknown_manifest_data))
        with self.assertRaises(SystemExit):
            check.check(instream)

    def test_branch_defaults_to_HEAD(self):
        no_revision_data = self.demo_manifests_source
        no_revision_data['source']['revision'] = None
        instream = StringIO(json.dumps(no_revision_data))
        check.check(instream)

    def test_manifest_name_defaults(self):
        d = {
            'source': {
                'url': 'https://android.googlesource.com/tools/manifest',
                'revision': 'fetch_artifact-dev'
            },
        }
        instream = StringIO(json.dumps(d))
        check.check(instream)
        # no assert/assumption to call. repo init and sync should
        # just be called. maybe we can check for a file as well
        readme = common.CACHEDIR / 'fetch_artifact' / 'README.md'
        self.assertTrue(readme.exists())

    # so here, we init from a public manifest
    # init is completely working fine
    # but sync will fail miserably because one of the projects
    # is un-reachable
    def test_unreachable_projects_in_manifest(self):
        unreachable_projects_data = self.demo_manifests_source
        unreachable_projects_data['source']['name'] = 'unreachable_project.xml'

        instream = StringIO(json.dumps(unreachable_projects_data))
        with self.assertRaises(SystemExit):
            check.check(instream)

    def test_first_revision(self):
        data = self.demo_manifests_source
        instream = StringIO(json.dumps(data))
        versions = check.check(instream)
        # we passed no version as input, so we should just get current version
        self.assertEqual(len(versions), 1)

    def test_same_revision(self):
        data = self.demo_manifests_source
        data['versions'] = [{
            'version':
            '<?xml version="1.0" encoding="UTF-8"?>\n<manifest>\n  <remote name="aosp" fetch="https://android.googlesource.com/"/>\n  \n  <default remote="aosp" revision="refs/tags/android-12.0.0_r32"/>\n  \n  <project name="device/generic/common" revision="033d50e2298811d81de7db8cdea63e349a96c9ba" upstream="refs/tags/android-12.0.0_r32" dest-branch="refs/tags/android-12.0.0_r32" groups="pdk"/>\n</manifest>\n'  # noqa: E501
        }]
        instream = StringIO(json.dumps(data))
        versions = check.check(instream)
        # we passed the same version so we should only get one result
        self.assertEqual(len(versions), 1)

    # here we need a hard-coded manifest
    # which also contains hard-coded revisions to make
    # sure nothing ever moves
    def test_known_version(self):
        data = self.demo_manifests_source
        instream = StringIO(json.dumps(data))
        versions = check.check(instream)
        # we passed no version as input, so we should just get current version
        self.assertEqual(len(versions), 1)
        # and we know that version
        expected_version = '<?xml version="1.0" encoding="UTF-8"?>\n<manifest>\n  <remote name="aosp" fetch="https://android.googlesource.com/"/>\n  \n  <default remote="aosp" revision="refs/tags/android-12.0.0_r32"/>\n  \n  <project name="device/generic/common" revision="033d50e2298811d81de7db8cdea63e349a96c9ba" upstream="refs/tags/android-12.0.0_r32" dest-branch="refs/tags/android-12.0.0_r32" groups="pdk"/>\n</manifest>\n'  # noqa: E501
        version = versions[0]['version']
        self.assertEqual(version, expected_version)

    # we can reuse the same hard-coded manifest here
    # but we use a newer version (using a different git branch)
    def test_new_revision(self):
        data = self.demo_manifests_source
        data['versions'] = [{'version': 'older-shasum'}]
        instream = StringIO(json.dumps(data))
        versions = check.check(instream)
        self.assertEqual(len(versions), 2)
        expected_version = '<?xml version="1.0" encoding="UTF-8"?>\n<manifest>\n  <remote name="aosp" fetch="https://android.googlesource.com/"/>\n  \n  <default remote="aosp" revision="refs/tags/android-12.0.0_r32"/>\n  \n  <project name="device/generic/common" revision="033d50e2298811d81de7db8cdea63e349a96c9ba" upstream="refs/tags/android-12.0.0_r32" dest-branch="refs/tags/android-12.0.0_r32" groups="pdk"/>\n</manifest>\n'  # noqa: E501
        newest_version = versions[-1]['version']
        self.assertEqual(newest_version, expected_version)

    @unittest.skipUnless(
        Path('development/ssh/test_key').exists(), "requires ssh test key")
    def test_ssh_private_key(self):
        data = self.demo_ssh_manifests_source

        private_test_key = Path('development/ssh/test_key')
        data['source']['private_key'] = private_test_key.read_text()

        instream = StringIO(json.dumps(data))
        versions = check.check(instream)
        # we passed no version as input, so we should just get current version
        self.assertEqual(len(versions), 1)


if __name__ == '__main__':
    unittest.main()
