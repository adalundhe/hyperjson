# SPDX-License-Identifier: (Apache-2.0 OR MIT)
# Copyright ijl (2018-2025)

import io
import sys

import pytest

import hyperjson

from .util import SUPPORTS_MEMORYVIEW


class TestType:
    def test_fragment(self):
        """
        hyperjson.JSONDecodeError on fragments
        """
        for val in ("n", "{", "[", "t"):
            pytest.raises(hyperjson.JSONDecodeError, hyperjson.loads, val)

    def test_invalid(self):
        """
        hyperjson.JSONDecodeError on invalid
        """
        for val in ('{"age", 44}', "[31337,]", "[,31337]", "[]]", "[,]"):
            pytest.raises(hyperjson.JSONDecodeError, hyperjson.loads, val)

    def test_str(self):
        """
        str
        """
        for obj, ref in (("blah", b'"blah"'), ("東京", b'"\xe6\x9d\xb1\xe4\xba\xac"')):
            assert hyperjson.dumps(obj) == ref
            assert hyperjson.loads(ref) == obj

    def test_str_latin1(self):
        """
        str latin1
        """
        assert hyperjson.loads(hyperjson.dumps("üýþÿ")) == "üýþÿ"

    def test_str_long(self):
        """
        str long
        """
        for obj in ("aaaa" * 1024, "üýþÿ" * 1024, "好" * 1024, "�" * 1024):
            assert hyperjson.loads(hyperjson.dumps(obj)) == obj

    def test_str_2mib(self):
        ref = '🐈🐈🐈🐈🐈"üýa0s9999🐈🐈🐈🐈🐈9\0999\\9999' * 1024 * 50
        assert hyperjson.loads(hyperjson.dumps(ref)) == ref

    def test_str_very_long(self):
        """
        str long enough to trigger overflow in bytecount
        """
        for obj in ("aaaa" * 20000, "üýþÿ" * 20000, "好" * 20000, "�" * 20000):
            assert hyperjson.loads(hyperjson.dumps(obj)) == obj

    def test_str_replacement(self):
        """
        str roundtrip �
        """
        assert hyperjson.dumps("�") == b'"\xef\xbf\xbd"'
        assert hyperjson.loads(b'"\xef\xbf\xbd"') == "�"

    def test_str_trailing_4_byte(self):
        ref = "うぞ〜😏🙌"
        assert hyperjson.loads(hyperjson.dumps(ref)) == ref

    def test_str_ascii_control(self):
        """
        worst case format_escaped_str_with_escapes() allocation
        """
        ref = "\x01\x1f" * 1024 * 16
        assert hyperjson.loads(hyperjson.dumps(ref)) == ref
        assert (
            hyperjson.loads(hyperjson.dumps(ref, option=hyperjson.OPT_INDENT_2)) == ref
        )

    def test_str_escape_quote_0(self):
        assert hyperjson.dumps('"aaaaaaabb') == b'"\\"aaaaaaabb"'

    def test_str_escape_quote_1(self):
        assert hyperjson.dumps('a"aaaaaabb') == b'"a\\"aaaaaabb"'

    def test_str_escape_quote_2(self):
        assert hyperjson.dumps('aa"aaaaabb') == b'"aa\\"aaaaabb"'

    def test_str_escape_quote_3(self):
        assert hyperjson.dumps('aaa"aaaabb') == b'"aaa\\"aaaabb"'

    def test_str_escape_quote_4(self):
        assert hyperjson.dumps('aaaa"aaabb') == b'"aaaa\\"aaabb"'

    def test_str_escape_quote_5(self):
        assert hyperjson.dumps('aaaaa"aabb') == b'"aaaaa\\"aabb"'

    def test_str_escape_quote_6(self):
        assert hyperjson.dumps('aaaaaa"abb') == b'"aaaaaa\\"abb"'

    def test_str_escape_quote_7(self):
        assert hyperjson.dumps('aaaaaaa"bb') == b'"aaaaaaa\\"bb"'

    def test_str_escape_quote_8(self):
        assert hyperjson.dumps('aaaaaaaab"') == b'"aaaaaaaab\\""'

    def test_str_escape_quote_multi(self):
        assert (
            hyperjson.dumps('aa"aaaaabbbbbbbbbbbbbbbbbbbb"bb')
            == b'"aa\\"aaaaabbbbbbbbbbbbbbbbbbbb\\"bb"'
        )

    def test_str_escape_quote_buffer(self):
        hyperjson.dumps(['"' * 4096] * 1024)

    def test_str_escape_backslash_0(self):
        assert hyperjson.dumps("\\aaaaaaabb") == b'"\\\\aaaaaaabb"'

    def test_str_escape_backslash_1(self):
        assert hyperjson.dumps("a\\aaaaaabb") == b'"a\\\\aaaaaabb"'

    def test_str_escape_backslash_2(self):
        assert hyperjson.dumps("aa\\aaaaabb") == b'"aa\\\\aaaaabb"'

    def test_str_escape_backslash_3(self):
        assert hyperjson.dumps("aaa\\aaaabb") == b'"aaa\\\\aaaabb"'

    def test_str_escape_backslash_4(self):
        assert hyperjson.dumps("aaaa\\aaabb") == b'"aaaa\\\\aaabb"'

    def test_str_escape_backslash_5(self):
        assert hyperjson.dumps("aaaaa\\aabb") == b'"aaaaa\\\\aabb"'

    def test_str_escape_backslash_6(self):
        assert hyperjson.dumps("aaaaaa\\abb") == b'"aaaaaa\\\\abb"'

    def test_str_escape_backslash_7(self):
        assert hyperjson.dumps("aaaaaaa\\bb") == b'"aaaaaaa\\\\bb"'

    def test_str_escape_backslash_8(self):
        assert hyperjson.dumps("aaaaaaaab\\") == b'"aaaaaaaab\\\\"'

    def test_str_escape_backslash_multi(self):
        assert (
            hyperjson.dumps("aa\\aaaaabbbbbbbbbbbbbbbbbbbb\\bb")
            == b'"aa\\\\aaaaabbbbbbbbbbbbbbbbbbbb\\\\bb"'
        )

    def test_str_escape_backslash_buffer(self):
        hyperjson.dumps(["\\" * 4096] * 1024)

    def test_str_escape_x32_0(self):
        assert hyperjson.dumps("\taaaaaaabb") == b'"\\taaaaaaabb"'

    def test_str_escape_x32_1(self):
        assert hyperjson.dumps("a\taaaaaabb") == b'"a\\taaaaaabb"'

    def test_str_escape_x32_2(self):
        assert hyperjson.dumps("aa\taaaaabb") == b'"aa\\taaaaabb"'

    def test_str_escape_x32_3(self):
        assert hyperjson.dumps("aaa\taaaabb") == b'"aaa\\taaaabb"'

    def test_str_escape_x32_4(self):
        assert hyperjson.dumps("aaaa\taaabb") == b'"aaaa\\taaabb"'

    def test_str_escape_x32_5(self):
        assert hyperjson.dumps("aaaaa\taabb") == b'"aaaaa\\taabb"'

    def test_str_escape_x32_6(self):
        assert hyperjson.dumps("aaaaaa\tabb") == b'"aaaaaa\\tabb"'

    def test_str_escape_x32_7(self):
        assert hyperjson.dumps("aaaaaaa\tbb") == b'"aaaaaaa\\tbb"'

    def test_str_escape_x32_8(self):
        assert hyperjson.dumps("aaaaaaaab\t") == b'"aaaaaaaab\\t"'

    def test_str_escape_x32_multi(self):
        assert (
            hyperjson.dumps("aa\taaaaabbbbbbbbbbbbbbbbbbbb\tbb")
            == b'"aa\\taaaaabbbbbbbbbbbbbbbbbbbb\\tbb"'
        )

    def test_str_escape_x32_buffer(self):
        hyperjson.dumps(["\t" * 4096] * 1024)

    def test_str_emoji(self):
        ref = "®️"
        assert hyperjson.loads(hyperjson.dumps(ref)) == ref

    def test_str_emoji_escape(self):
        ref = '/"®️/"'
        assert hyperjson.loads(hyperjson.dumps(ref)) == ref

    def test_very_long_list(self):
        hyperjson.dumps([[]] * 1024 * 16)

    def test_very_long_list_pretty(self):
        hyperjson.dumps([[]] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_dict(self):
        hyperjson.dumps([{}] * 1024 * 16)

    def test_very_long_dict_pretty(self):
        hyperjson.dumps([{}] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_str_empty(self):
        hyperjson.dumps([""] * 1024 * 16)

    def test_very_long_str_empty_pretty(self):
        hyperjson.dumps([""] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_str_not_empty(self):
        hyperjson.dumps(["a"] * 1024 * 16)

    def test_very_long_str_not_empty_pretty(self):
        hyperjson.dumps(["a"] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_bool(self):
        hyperjson.dumps([True] * 1024 * 16)

    def test_very_long_bool_pretty(self):
        hyperjson.dumps([True] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_int(self):
        hyperjson.dumps([(2**64) - 1] * 1024 * 16)

    def test_very_long_int_pretty(self):
        hyperjson.dumps([(2**64) - 1] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_very_long_float(self):
        hyperjson.dumps([sys.float_info.max] * 1024 * 16)

    def test_very_long_float_pretty(self):
        hyperjson.dumps([sys.float_info.max] * 1024 * 16, option=hyperjson.OPT_INDENT_2)

    def test_str_surrogates_loads(self):
        """
        str unicode surrogates loads()
        """
        pytest.raises(hyperjson.JSONDecodeError, hyperjson.loads, '"\ud800"')
        pytest.raises(hyperjson.JSONDecodeError, hyperjson.loads, '"\ud83d\ude80"')
        pytest.raises(hyperjson.JSONDecodeError, hyperjson.loads, '"\udcff"')
        pytest.raises(
            hyperjson.JSONDecodeError,
            hyperjson.loads,
            b'"\xed\xa0\xbd\xed\xba\x80"',
        )  # \ud83d\ude80

    def test_str_surrogates_dumps(self):
        """
        str unicode surrogates dumps()
        """
        pytest.raises(hyperjson.JSONEncodeError, hyperjson.dumps, "\ud800")
        pytest.raises(hyperjson.JSONEncodeError, hyperjson.dumps, "\ud83d\ude80")
        pytest.raises(hyperjson.JSONEncodeError, hyperjson.dumps, "\udcff")
        pytest.raises(
            hyperjson.JSONEncodeError,
            hyperjson.dumps,
            {"\ud83d\ude80": None},
        )
        pytest.raises(
            hyperjson.JSONEncodeError,
            hyperjson.dumps,
            b"\xed\xa0\xbd\xed\xba\x80",
        )  # \ud83d\ude80

    def test_bytes_dumps(self):
        """
        bytes dumps not supported
        """
        with pytest.raises(hyperjson.JSONEncodeError):
            hyperjson.dumps([b"a"])

    def test_bytes_loads(self):
        """
        bytes loads
        """
        assert hyperjson.loads(b"[]") == []

    def test_bytearray_loads(self):
        """
        bytearray loads
        """
        arr = bytearray()
        arr.extend(b"[]")
        assert hyperjson.loads(arr) == []

    @pytest.mark.skipif(SUPPORTS_MEMORYVIEW, reason="memoryview not supported")
    def test_memoryview_loads_supported(self):
        """
        memoryview loads supported
        """
        arr = bytearray()
        arr.extend(b"[]")
        assert hyperjson.loads(memoryview(arr)) == []

    @pytest.mark.skipif(not SUPPORTS_MEMORYVIEW, reason="memoryview supported")
    def test_memoryview_loads_unsupported(self):
        """
        memoryview loads unsupported
        """
        arr = bytearray()
        arr.extend(b"[]")
        with pytest.raises(hyperjson.JSONEncodeError):
            hyperjson.loads(memoryview(arr))

    def test_bytesio_loads(self):
        """
        BytesIO loads
        """
        arr = io.BytesIO(b"[]")
        assert hyperjson.loads(arr.getbuffer()) == []

    def test_bool(self):
        """
        bool
        """
        for obj, ref in ((True, "true"), (False, "false")):
            assert hyperjson.dumps(obj) == ref.encode("utf-8")
            assert hyperjson.loads(ref) == obj

    def test_bool_true_array(self):
        """
        bool true array
        """
        obj = [True] * 256
        ref = ("[" + ("true," * 255) + "true]").encode("utf-8")
        assert hyperjson.dumps(obj) == ref
        assert hyperjson.loads(ref) == obj

    def test_bool_false_array(self):
        """
        bool false array
        """
        obj = [False] * 256
        ref = ("[" + ("false," * 255) + "false]").encode("utf-8")
        assert hyperjson.dumps(obj) == ref
        assert hyperjson.loads(ref) == obj

    def test_none(self):
        """
        null
        """
        obj = None
        ref = "null"
        assert hyperjson.dumps(obj) == ref.encode("utf-8")
        assert hyperjson.loads(ref) == obj

    def test_int(self):
        """
        int compact and non-compact
        """
        obj = [-5000, -1000, -10, -5, -2, -1, 0, 1, 2, 5, 10, 1000, 50000]
        ref = b"[-5000,-1000,-10,-5,-2,-1,0,1,2,5,10,1000,50000]"
        assert hyperjson.dumps(obj) == ref
        assert hyperjson.loads(ref) == obj

    def test_null_array(self):
        """
        null array
        """
        obj = [None] * 256
        ref = ("[" + ("null," * 255) + "null]").encode("utf-8")
        assert hyperjson.dumps(obj) == ref
        assert hyperjson.loads(ref) == obj

    def test_nan_dumps(self):
        """
        NaN serializes to null
        """
        assert hyperjson.dumps(float("NaN")) == b"null"

    def test_nan_loads(self):
        """
        NaN is not valid JSON
        """
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[NaN]")
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[nan]")

    def test_infinity_dumps(self):
        """
        Infinity serializes to null
        """
        assert hyperjson.dumps(float("Infinity")) == b"null"

    def test_infinity_loads(self):
        """
        Infinity, -Infinity is not valid JSON
        """
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[infinity]")
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[Infinity]")
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[-Infinity]")
        with pytest.raises(hyperjson.JSONDecodeError):
            hyperjson.loads("[-infinity]")

    def test_int_53(self):
        """
        int 53-bit
        """
        for val in (9007199254740991, -9007199254740991):
            assert hyperjson.loads(str(val)) == val
            assert hyperjson.dumps(val, option=hyperjson.OPT_STRICT_INTEGER) == str(
                val,
            ).encode("utf-8")

    def test_int_53_exc(self):
        """
        int 53-bit exception on 64-bit
        """
        for val in (9007199254740992, -9007199254740992):
            with pytest.raises(hyperjson.JSONEncodeError):
                hyperjson.dumps(val, option=hyperjson.OPT_STRICT_INTEGER)

    def test_int_53_exc_usize(self):
        """
        int 53-bit exception on 64-bit usize
        """
        for val in (9223372036854775808, 18446744073709551615):
            with pytest.raises(hyperjson.JSONEncodeError):
                hyperjson.dumps(val, option=hyperjson.OPT_STRICT_INTEGER)

    def test_int_53_exc_128(self):
        """
        int 53-bit exception on 128-bit
        """
        val = 2**65
        with pytest.raises(hyperjson.JSONEncodeError):
            hyperjson.dumps(val, option=hyperjson.OPT_STRICT_INTEGER)

    def test_int_64(self):
        """
        int 64-bit
        """
        for val in (9223372036854775807, -9223372036854775807):
            assert hyperjson.loads(str(val)) == val
            assert hyperjson.dumps(val) == str(val).encode("utf-8")

    def test_uint_64(self):
        """
        uint 64-bit
        """
        for val in (0, 9223372036854775808, 18446744073709551615):
            assert hyperjson.loads(str(val)) == val
            assert hyperjson.dumps(val) == str(val).encode("utf-8")

    def test_int_128(self):
        """
        int 128-bit
        """
        for val in (18446744073709551616, -9223372036854775809):
            pytest.raises(hyperjson.JSONEncodeError, hyperjson.dumps, val)

    def test_float(self):
        """
        float
        """
        assert -1.1234567893 == hyperjson.loads("-1.1234567893")
        assert -1.234567893 == hyperjson.loads("-1.234567893")
        assert -1.34567893 == hyperjson.loads("-1.34567893")
        assert -1.4567893 == hyperjson.loads("-1.4567893")
        assert -1.567893 == hyperjson.loads("-1.567893")
        assert -1.67893 == hyperjson.loads("-1.67893")
        assert -1.7893 == hyperjson.loads("-1.7893")
        assert -1.893 == hyperjson.loads("-1.893")
        assert -1.3 == hyperjson.loads("-1.3")

        assert 1.1234567893 == hyperjson.loads("1.1234567893")
        assert 1.234567893 == hyperjson.loads("1.234567893")
        assert 1.34567893 == hyperjson.loads("1.34567893")
        assert 1.4567893 == hyperjson.loads("1.4567893")
        assert 1.567893 == hyperjson.loads("1.567893")
        assert 1.67893 == hyperjson.loads("1.67893")
        assert 1.7893 == hyperjson.loads("1.7893")
        assert 1.893 == hyperjson.loads("1.893")
        assert 1.3 == hyperjson.loads("1.3")

    def test_float_precision_loads(self):
        """
        float precision loads()
        """
        assert hyperjson.loads("31.245270191439438") == 31.245270191439438
        assert hyperjson.loads("-31.245270191439438") == -31.245270191439438
        assert hyperjson.loads("121.48791951161945") == 121.48791951161945
        assert hyperjson.loads("-121.48791951161945") == -121.48791951161945
        assert hyperjson.loads("100.78399658203125") == 100.78399658203125
        assert hyperjson.loads("-100.78399658203125") == -100.78399658203125

    def test_float_precision_dumps(self):
        """
        float precision dumps()
        """
        assert hyperjson.dumps(31.245270191439438) == b"31.245270191439438"
        assert hyperjson.dumps(-31.245270191439438) == b"-31.245270191439438"
        assert hyperjson.dumps(121.48791951161945) == b"121.48791951161945"
        assert hyperjson.dumps(-121.48791951161945) == b"-121.48791951161945"
        assert hyperjson.dumps(100.78399658203125) == b"100.78399658203125"
        assert hyperjson.dumps(-100.78399658203125) == b"-100.78399658203125"

    def test_float_edge(self):
        """
        float edge cases
        """
        assert hyperjson.dumps(0.8701) == b"0.8701"

        assert hyperjson.loads("0.8701") == 0.8701
        assert (
            hyperjson.loads("0.0000000000000000000000000000000000000000000000000123e50")
            == 1.23
        )
        assert hyperjson.loads("0.4e5") == 40000.0
        assert hyperjson.loads("0.00e-00") == 0.0
        assert hyperjson.loads("0.4e-001") == 0.04
        assert hyperjson.loads("0.123456789e-12") == 1.23456789e-13
        assert hyperjson.loads("1.234567890E+34") == 1.23456789e34
        assert hyperjson.loads("23456789012E66") == 2.3456789012e76

    def test_float_notation(self):
        """
        float notation
        """
        for val in ("1.337E40", "1.337e+40", "1337e40", "1.337E-4"):
            obj = hyperjson.loads(val)
            assert obj == float(val)
            assert hyperjson.dumps(val) == (f'"{val}"').encode("utf-8")

    def test_list(self):
        """
        list
        """
        obj = ["a", "😊", True, {"b": 1.1}, 2]
        ref = '["a","😊",true,{"b":1.1},2]'
        assert hyperjson.dumps(obj) == ref.encode("utf-8")
        assert hyperjson.loads(ref) == obj

    def test_tuple(self):
        """
        tuple
        """
        obj = ("a", "😊", True, {"b": 1.1}, 2)
        ref = '["a","😊",true,{"b":1.1},2]'
        assert hyperjson.dumps(obj) == ref.encode("utf-8")
        assert hyperjson.loads(ref) == list(obj)

    def test_object(self):
        """
        object() dumps()
        """
        with pytest.raises(hyperjson.JSONEncodeError):
            hyperjson.dumps(object())
