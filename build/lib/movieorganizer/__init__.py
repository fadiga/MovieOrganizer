# encoding=utf-8
# mainteneur: Fadiga

"""
MovieOrganizer - Organise les fichiers de films et séries téléchargés.
"""

from movieorganizer.organize import (
    calculate_similarity,
    clean_filename,
    get_target_folder,
    process_downloads,
)


def main():
    """Point d'entrée pour la commande movieorganizer."""
    from movieorganizer.organize import run

    run()


__all__ = [
    "calculate_similarity",
    "clean_filename",
    "get_target_folder",
    "main",
    "process_downloads",
]
