# encoding=utf-8
# mainteneur: Fadiga

import configparser
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_config() -> configparser.ConfigParser:
    """Charge la configuration depuis config.ini (cwd prioritaire, puis package)."""
    config = configparser.ConfigParser()
    config_paths = [
        Path.cwd() / "config.ini",
        Path.home() / ".config" / "movieorganizer" / "config.ini",
    ]
    # Config par défaut du package
    try:
        from importlib.resources import files

        pkg_config = files("movieorganizer") / "config.ini"
        if pkg_config.is_file():
            config_paths.append(pkg_config)
    except (ImportError, AttributeError):
        pass
    config.read([str(p) for p in config_paths if p.exists()])
    return config


def _init_from_config(config: configparser.ConfigParser) -> dict:
    """Initialise les variables depuis la configuration."""
    dest_folder = Path(config["paths"]["dest_folder"]).expanduser().resolve()
    downloads_folder = Path(config["paths"]["path_dl_files"]).expanduser().resolve()
    video_extensions = set(config["extensions"]["list_extension"].split(","))
    delete_extensions = set(config["extensions"]["file_dl"].split(","))
    deleted_patterns = [
        re.compile(pattern.strip())
        for pattern in config["patterns"]["elt_deleted_patterns"].split(",")
    ]
    series_regex = re.compile(config["patterns"]["series_pattern"])
    similarity_threshold = float(config["patterns"]["similarity_threshold"])
    return {
        "dest_folder": dest_folder,
        "downloads_folder": downloads_folder,
        "video_extensions": video_extensions,
        "delete_extensions": delete_extensions,
        "deleted_patterns": deleted_patterns,
        "series_regex": series_regex,
        "similarity_threshold": similarity_threshold,
    }


def clean_filename(filename: str, deleted_patterns: list = None) -> str:
    """
    Nettoie le nom de fichier en supprimant les éléments indésirables au début.
    """
    if deleted_patterns is None:
        config = _load_config()
        ctx = _init_from_config(config)
        deleted_patterns = ctx["deleted_patterns"]
    for pattern in deleted_patterns:
        if pattern.match(filename):
            return pattern.sub("", filename)
    return filename


def get_target_folder(
    filename: str,
    dest_folder: Path = None,
    series_regex: re.Pattern = None,
) -> Path:
    """
    Détermine le dossier de destination en fonction du nom de fichier.
    Les séries sont organisées par nom de série et saison.
    """
    if dest_folder is None or series_regex is None:
        config = _load_config()
        ctx = _init_from_config(config)
        dest_folder = dest_folder or ctx["dest_folder"]
        series_regex = series_regex or ctx["series_regex"]
    match = series_regex.match(filename)
    if match:
        series_name = match.group("series").strip()
        season = match.group("season")
        if season:
            return dest_folder / "Series" / series_name / f"Season {season}"
    return dest_folder / "Movies"


def process_downloads(
    source_dir: Path,
    dest_dir: Path,
    *,
    video_extensions: set = None,
    delete_extensions: set = None,
    deleted_patterns: list = None,
    series_regex: re.Pattern = None,
    similarity_threshold: float = None,
):
    """
    Traite les fichiers dans le répertoire source en les déplaçant vers le répertoire de destination
    et en supprimant les fichiers indésirables.
    """
    config = _load_config()
    ctx = _init_from_config(config)
    video_extensions = video_extensions or ctx["video_extensions"]
    delete_extensions = delete_extensions or ctx["delete_extensions"]
    deleted_patterns = deleted_patterns or ctx["deleted_patterns"]
    series_regex = series_regex or ctx["series_regex"]
    similarity_threshold = similarity_threshold or ctx["similarity_threshold"]

    logger.info("---------TRAITEMENT DES FICHIERS-------------------\n")
    total_files = 0
    moved_files = 0

    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            file_extension = file_path.suffix.lstrip(".")
            total_files += 1

            if file_extension in delete_extensions:
                file_path.unlink()
                logger.info(f"Supprimé : {file_path}")
                total_files -= 1
                continue

            if file_extension in video_extensions or series_regex.match(file_path.name):
                cleaned_name = clean_filename(file_path.name, deleted_patterns)
                target_folder = get_target_folder(
                    cleaned_name, dest_folder=dest_dir, series_regex=series_regex
                )
                target_path = target_folder / cleaned_name

                if not target_folder.exists():
                    target_folder.mkdir(parents=True, exist_ok=True)

                file_path.rename(target_path)
                moved_files += 1
                logger.info(f"{file_path.name} -----> {target_path}")

    _organize_movies(dest_dir / "Movies", similarity_threshold)

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


def _organize_movies(movies_folder: Path, similarity_threshold: float):
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
            if calculate_similarity(base_file.stem, file.stem) > similarity_threshold:
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


def run():
    """Exécute l'organisation des médias selon la configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    config = _load_config()
    ctx = _init_from_config(config)
    process_downloads(ctx["downloads_folder"], ctx["dest_folder"])
