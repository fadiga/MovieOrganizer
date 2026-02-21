import tempfile
from pathlib import Path

import pytest

from movieorganizer import calculate_similarity, clean_filename, get_target_folder


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


def test_clean_filename(temp_dir):
    filename_with_prefix = "[www.banakou.com] Test Movie.mp4"
    # Le motif supprime le préfixe, un espace peut rester
    cleaned_filename = clean_filename(filename_with_prefix)

    assert cleaned_filename.strip() == "Test Movie.mp4"


def test_get_target_folder(temp_dir):
    series_filename = "Series Name - S01E01.mp4"
    non_series_filename = "Random Movie.mp4"

    target_folder_for_series = get_target_folder(
        series_filename, dest_folder=temp_dir
    )
    # S01 donne "Season 01" (format du motif regex)
    assert target_folder_for_series == temp_dir / "Series" / "Series Name" / "Season 01"

    target_folder_for_movie = get_target_folder(
        non_series_filename, dest_folder=temp_dir
    )
    assert target_folder_for_movie == temp_dir / "Movies"


def test_calculate_similarity():
    assert calculate_similarity("test", "test") == 1.0
    assert calculate_similarity("test", "tset") >= 0.7  # anagramme partiel
    assert calculate_similarity("test", "example") < 0.5
