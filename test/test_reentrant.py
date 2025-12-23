# SPDX-License-Identifier: (Apache-2.0 OR MIT)
# Copyright Anders Kaseorg (2023)
import hyperjson


class C:
    c: "C"

    def __del__(self):
        hyperjson.loads('"' + "a" * 10000 + '"')


def test_reentrant():
    c = C()
    c.c = c
    del c

    hyperjson.loads("[" + "[]," * 1000 + "[]]")
