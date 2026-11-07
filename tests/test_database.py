"""Regression tests for the primitive database."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from primitive_db import core, parser, utils
from primitive_db.decorators import create_cacher


class DatabaseTests(unittest.TestCase):
    """Test schema, persistence, CRUD and parsing."""

    def test_schema_and_validation(self):
        metadata = {}
        core.create_table(metadata, "users", ["name:str", "age:int", "active:bool"])
        self.assertEqual(metadata["users"][0], "ID:int")
        with self.assertRaises(ValueError):
            core.create_table(metadata, "users", ["name:str"])
        with self.assertRaises(ValueError):
            core.create_table(metadata, "bad", ["age:float"])
        with self.assertRaises(ValueError):
            core.create_table(metadata, "bad", ["ID:int"])

    def test_crud(self):
        metadata = {"users": ["ID:int", "name:str", "age:int", "active:bool"]}
        with patch.object(core, "load_table_data", return_value=[]):
            rows = core.insert(metadata, "users", ["Sergei", 28, True])
        self.assertEqual(rows[0]["ID"], 1)
        self.assertEqual(core.select(rows, {"age": 28})[0]["name"], "Sergei")
        core.update(rows, {"age": 29}, {"name": "Sergei"})
        self.assertEqual(core.select(rows, {"age": 29})[0]["ID"], 1)
        with patch("builtins.input", return_value="y"):
            core.delete(rows, {"ID": 1})
        self.assertEqual(rows, [])
        with patch.object(core, "load_table_data", return_value=[]):
            with self.assertRaises(ValueError):
                core.insert(metadata, "users", ["Sergei", "28", True])

    def test_confirmation(self):
        metadata = {"users": ["ID:int"]}
        with patch("builtins.input", return_value="n"):
            self.assertIsNone(core.drop_table(metadata, "users"))
        self.assertIn("users", metadata)
        with patch("builtins.input", return_value="y"):
            core.drop_table(metadata, "users")
        self.assertNotIn("users", metadata)

    def test_parser(self):
        self.assertEqual(parser.parse_values('("A, B", 3, false)'), ["A, B", 3, False])
        self.assertEqual(parser.parse_condition('name = "Sergei"'), {"name": "Sergei"})
        with self.assertRaises(ValueError):
            parser.parse_values("(A, 3)")

    def test_metadata_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "db_meta.json"
            self.assertEqual(utils.load_metadata(path), {})
            utils.save_metadata(path, {"users": ["ID:int"]})
            self.assertEqual(utils.load_metadata(path), {"users": ["ID:int"]})

    def test_cache_closure(self):
        calls = []
        cacher = create_cacher()

        def calculate():
            calls.append(1)
            return 42

        self.assertEqual(cacher("key", calculate), 42)
        self.assertEqual(cacher("key", calculate), 42)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
