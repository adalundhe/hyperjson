# SPDX-License-Identifier: (Apache-2.0 OR MIT)
# Copyright ijl (2020-2025)

import hyperjson

from .util import needs_data, read_fixture_obj


class TestAppendNewline:
    def test_dumps_newline(self):
        """
        dumps() OPT_APPEND_NEWLINE
        """
        assert hyperjson.dumps([], option=hyperjson.OPT_APPEND_NEWLINE) == b"[]\n"

    @needs_data
    def test_twitter_newline(self):
        """
        loads(),dumps() twitter.json OPT_APPEND_NEWLINE
        """
        val = read_fixture_obj("twitter.json.xz")
        assert hyperjson.loads(hyperjson.dumps(val, option=hyperjson.OPT_APPEND_NEWLINE)) == val

    @needs_data
    def test_canada(self):
        """
        loads(), dumps() canada.json OPT_APPEND_NEWLINE
        """
        val = read_fixture_obj("canada.json.xz")
        assert hyperjson.loads(hyperjson.dumps(val, option=hyperjson.OPT_APPEND_NEWLINE)) == val

    @needs_data
    def test_citm_catalog_newline(self):
        """
        loads(), dumps() citm_catalog.json OPT_APPEND_NEWLINE
        """
        val = read_fixture_obj("citm_catalog.json.xz")
        assert hyperjson.loads(hyperjson.dumps(val, option=hyperjson.OPT_APPEND_NEWLINE)) == val

    @needs_data
    def test_github_newline(self):
        """
        loads(), dumps() github.json OPT_APPEND_NEWLINE
        """
        val = read_fixture_obj("github.json.xz")
        assert hyperjson.loads(hyperjson.dumps(val, option=hyperjson.OPT_APPEND_NEWLINE)) == val
