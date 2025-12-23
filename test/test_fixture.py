# SPDX-License-Identifier: (Apache-2.0 OR MIT)
# Copyright ijl (2018-2025)

import pytest

import hyperjson

from .util import needs_data, read_fixture_bytes, read_fixture_str


@needs_data
class TestFixture:
    def test_twitter(self):
        """
        loads(),dumps() twitter.json
        """
        val = read_fixture_str("twitter.json.xz")
        read = hyperjson.loads(val)
        assert hyperjson.loads(hyperjson.dumps(read)) == read

    @needs_data
    def test_canada(self):
        """
        loads(), dumps() canada.json
        """
        val = read_fixture_str("canada.json.xz")
        read = hyperjson.loads(val)
        assert hyperjson.loads(hyperjson.dumps(read)) == read

    def test_citm_catalog(self):
        """
        loads(), dumps() citm_catalog.json
        """
        val = read_fixture_str("citm_catalog.json.xz")
        read = hyperjson.loads(val)
        assert hyperjson.loads(hyperjson.dumps(read)) == read

    def test_github(self):
        """
        loads(), dumps() github.json
        """
        val = read_fixture_str("github.json.xz")
        read = hyperjson.loads(val)
        assert hyperjson.loads(hyperjson.dumps(read)) == read

    def test_blns(self):
        """
        loads() blns.json JSONDecodeError

        https://github.com/minimaxir/big-list-of-naughty-strings
        """
        val = read_fixture_bytes("blns.txt.xz")
        for line in val.split(b"\n"):
            if line and not line.startswith(b"#"):
                with pytest.raises(hyperjson.JSONDecodeError):
                    _ = hyperjson.loads(b'"' + val + b'"')
