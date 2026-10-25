"""Test del parsing tollerante (M1): scala di degradazione deterministica."""

import unittest

from pdfbook.translation.json_repair import (
    JsonRepairError,
    escape_unescaped_quotes,
    parse_json_object,
    strip_code_fence,
)


class DirectJsonTest(unittest.TestCase):
    def test_valid_object(self):
        parsed = parse_json_object('{"a": "ciao", "b": "mondo"}')
        self.assertEqual(parsed, {"a": "ciao", "b": "mondo"})

    def test_numeric_values_become_strings(self):
        self.assertEqual(parse_json_object('{"n": 42}'), {"n": "42"})

    def test_non_object_json_is_rejected(self):
        with self.assertRaises(JsonRepairError):
            parse_json_object('["a", "b"]')

    def test_bool_values_are_dropped(self):
        self.assertEqual(parse_json_object('{"a": "x", "b": true}'), {"a": "x"})


class FenceTest(unittest.TestCase):
    def test_strip_closed_fence(self):
        raw = '```json\n{"a": "b"}\n```'
        self.assertEqual(strip_code_fence(raw), '{"a": "b"}')
        self.assertEqual(parse_json_object(raw), {"a": "b"})

    def test_strip_unclosed_fence(self):
        raw = '```\n{"a": "b"}'
        self.assertEqual(parse_json_object(raw), {"a": "b"})

    def test_text_without_fence_is_unchanged(self):
        self.assertEqual(strip_code_fence(' {"a":"b"} '), '{"a":"b"}')


class RepairTest(unittest.TestCase):
    def test_unescaped_quotes_inside_value(self):
        raw = '{"a": "lui disse "ciao" e uscì", "b": "ok"}'
        parsed = parse_json_object(raw, expected_keys=["a", "b"])
        self.assertEqual(parsed["a"], 'lui disse "ciao" e uscì')
        self.assertEqual(parsed["b"], "ok")

    def test_braces_and_colons_inside_value(self):
        raw = '{"a": "usa {"x": 1} come esempio", "b": "fine"}'
        parsed = parse_json_object(raw, expected_keys=["a", "b"])
        self.assertIn("{", parsed["a"])
        self.assertEqual(parsed["b"], "fine")

    def test_newlines_inside_value(self):
        raw = '{"a": "prima\\nseconda", "b": "x"}'
        self.assertEqual(parse_json_object(raw)["a"], "prima\nseconda")

    def test_trailing_comma_and_structure(self):
        raw = '{"a": "x",\n "b": "y",}'
        parsed = parse_json_object(raw, expected_keys=["a", "b"])
        self.assertEqual(parsed, {"a": "x", "b": "y"})

    def test_missing_keys_are_skipped(self):
        parsed = parse_json_object('{"a": "x"}', expected_keys=["a", "mancante"])
        self.assertEqual(parsed, {"a": "x"})

    def test_expected_keys_are_deduplicated(self):
        parsed = parse_json_object('{"a": "x"}', expected_keys=["a", "a"])
        self.assertEqual(list(parsed), ["a"])

    def test_keys_with_dash_and_underscore(self):
        raw = '{"p1_b2-l3": "testo"}'
        self.assertEqual(parse_json_object(raw), {"p1_b2-l3": "testo"})

    def test_unrecoverable_payload_keeps_raw(self):
        with self.assertRaises(JsonRepairError) as ctx:
            parse_json_object("nessun json qui", expected_keys=["a"])
        self.assertIn("nessun json", ctx.exception.raw)

    def test_empty_payload(self):
        with self.assertRaises(JsonRepairError):
            parse_json_object("   ")

    def test_escape_helper_keeps_existing_escapes(self):
        self.assertEqual(escape_unescaped_quotes('a "b" \\"c\\"'), 'a \\"b\\" \\"c\\"')


if __name__ == "__main__":
    unittest.main()
