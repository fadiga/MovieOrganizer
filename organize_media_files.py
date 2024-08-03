#!/usr/bin/env python
# encoding=utf-8
# mainteneur: Fadiga

import configparser
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

# Configuration du logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lecture de la configuration depuis le fichier config.ini
config = configparser.ConfigParser()
config.read("config.ini")

# Définition des chemins de destination et de téléchargement
DESTINATION_FOLDER = Path(config["paths"]["dest_folder"]).expanduser().resolve()
DOWNLOADS_FOLDER = Path(config["paths"]["path_dl_files"]).expanduser().resolve()

# Extensions de fichiers pour les vidéos et les fichiers à supprimer
VIDEO_EXTENSIONS = set(config["extensions"]["list_extension"].split(","))
DELETE_EXTENSIONS = set(config["extensions"]["file_dl"].split(","))

# Motifs regex pour les éléments à supprimer au début des noms de fichiers
DELETED_PATTERNS = [
    re.compile(pattern.strip())
    for pattern in config["patterns"]["elt_deleted_patterns"].split(",")
]

# Motif regex pour identifier les séries et extraire les informations
SERIES_REGEX = re.compile(config["patterns"]["series_pattern"])

# Seuil de similarité pour regrouper les fichiers similaires
SIMILARITY_THRESHOLD = float(config["patterns"]["similarity_threshold"])


def clean_filename(filename: str) -> str:
    """
    Nettoie le nom de fichier en supprimant les éléments indésirables au début.
    """
    for pattern in DELETED_PATTERNS:
        if pattern.match(filename):
            return pattern.sub("", filename)
    return filename


def get_target_folder(filename: str) -> Path:
    """
    Détermine le dossier de destination en fonction du nom de fichier.
    Les séries sont organisées par nom de série et saison.
    """
    match = SERIES_REGEX.match(filename)
    if match:
        series_name = match.group("series").strip()
        season = match.group("season")
        if season:
            return DESTINATION_FOLDER / "Series" / series_name / f"Season {season}"
    return DESTINATION_FOLDER / "Movies"


def process_downloads(source_dir: Path, dest_dir: Path):
    """
    Traite les fichiers dans le répertoire source en les déplaçant vers le répertoire de destination
    et en supprimant les fichiers indésirables.
    """
    logger.info("---------TRAITEMENT DES FICHIERS-------------------\n")
    total_files = 0
    moved_files = 0

    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            file_extension = file_path.suffix.lstrip(".")
            total_files += 1

            if file_extension in DELETE_EXTENSIONS:
                file_path.unlink()
                logger.info(f"Supprimé : {file_path}")
                total_files -= 1
                continue

            if file_extension in VIDEO_EXTENSIONS or SERIES_REGEX.match(file_path.name):
                cleaned_name = clean_filename(file_path.name)
                target_folder = get_target_folder(cleaned_name)
                target_path = target_folder / cleaned_name

                if not target_folder.exists():
                    target_folder.mkdir(parents=True, exist_ok=True)

                file_path.rename(target_path)
                moved_files += 1
                logger.info(f"{file_path.name} -----> {target_path}")

    organize_movies(DESTINATION_FOLDER / "Movies")

    # Suppression des dossiers vides
    for dir_path in sorted(source_dir.rglob("*"), key=lambda p: -len(p.parts)):
        if dir_path.is_dir() and not list(dir_path.iterdir()):
            dir_path.rmdir()
            logger.info(f"Dossier supprimé : {dir_path}")

    logger.info(f"Nombre total de fichiers traités : {total_files}")
    logger.info(f"Nombre total de fichiers déplacés : {moved_files}")


def calculate_similarity(a: str, b: str) -> float:
    """
    Calcule la similarité entre deux chaînes de caractères en utilisant la méthode SequenceMatcher.
    """
    return SequenceMatcher(None, a, b).ratio()


def organize_movies(movies_folder: Path):
    """
    Organise les fichiers de films dans des sous-dossiers basés sur la similarité des noms de fichiers.
    """
    logger.info("---------ORGANISATION DES FILMS-------------------\n")
    files = list(movies_folder.glob("*"))

    grouped_files = []
    while files:
        base_file = files.pop(0)
        group = [base_file]
        for file in files[:]:
            if calculate_similarity(base_file.stem, file.stem) > SIMILARITY_THRESHOLD:
                group.append(file)
                files.remove(file)
        grouped_files.append(group)

    for group in grouped_files:
        if len(group) > 1:
            group_folder = movies_folder / group[0].stem
            group_folder.mkdir(exist_ok=True)
            for file in group:
                new_path = group_folder / file.name
                file.rename(new_path)
                logger.info(f"Déplacé {file.name} vers {new_path}")


if __name__ == "__main__":
    process_downloads(DOWNLOADS_FOLDER, DESTINATION_FOLDER)
