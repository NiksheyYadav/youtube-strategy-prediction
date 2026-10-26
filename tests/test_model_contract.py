"""Small, fast checks for the production feature contract."""

from __future__ import annotations

import unittest

from src.model_contract import (
    RAW_MODEL_COLUMNS,
    build_inference_design_matrix,
    make_input_row,
    normalise_tags,
)


class ModelContractTests(unittest.TestCase):
    def test_metadata_features_are_creator_known_and_deterministic(self) -> None:
        row = make_input_row(
            title="TOP 5 Study Tips! 📚",
            category_name="Education",
            tags="study, productivity|exam",
            description="Watch now: https://example.com #study Subscribe for more.",
            publish_day_of_week=0,
            publish_hour=18,
        )
        self.assertEqual(set(row), set(RAW_MODEL_COLUMNS))
        self.assertEqual(row["title_digit_count"], 1)
        self.assertEqual(row["title_exclamation_count"], 1)
        self.assertEqual(row["title_has_emoji"], 1)
        self.assertEqual(row["tag_count"], 3)
        self.assertEqual(row["description_url_count"], 1)
        self.assertEqual(row["description_has_hashtag"], 1)
        self.assertEqual(row["description_has_call_to_action"], 1)

    def test_empty_tags_are_not_counted_as_a_tag(self) -> None:
        self.assertEqual(normalise_tags("[none]"), [])
        self.assertEqual(normalise_tags(""), [])

    def test_live_matrix_is_aligned_to_the_training_schema(self) -> None:
        row = make_input_row("A title", "Education", "one|two", "Short description", 2, 9)
        expected = ["title_length", "category_name_Education", "category_name_Music"]
        matrix = build_inference_design_matrix([row], expected)
        self.assertEqual(matrix.columns.tolist(), expected)
        self.assertEqual(matrix.loc[0, "category_name_Education"], 1)
        self.assertEqual(matrix.loc[0, "category_name_Music"], 0)

    def test_invalid_time_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_input_row("Title", "Education", "", "", 7, 12)
        with self.assertRaises(ValueError):
            make_input_row("Title", "Education", "", "", 1, 24)


if __name__ == "__main__":
    unittest.main()
