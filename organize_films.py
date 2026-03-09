#!/usr/bin/env python3
"""
organize_films.py - Organise une bibliothèque de films

Usage:
    python organize_films.py <library_path> --dry-run
    python organize_films.py <library_path> --run

Conventions (CLAUDE.md):
    Films/
    └── Titre du Film (Année)/
        ├── Titre du Film (Année) [Qualité].mkv
        └── Subs/
                Titre du Film (Année).fr.srt
                Titre du Film (Année).nfo
    Collections: Titre (Collection)/Titre (Année)/...
    Extras/Featurettes/ : contenu non touché
"""

import os
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime

VIDEO_EXTS   = {'.mkv', '.mp4', '.avi', '.mov', '.m4v'}
SUB_EXTS     = {'.srt', '.sub', '.ass', '.ssa'}
KNOWN_LANGS  = ['pt-BR', 'pt-br', 'fr', 'en', 'es', 'de', 'it', 'ja', 'zh', 'ru', 'ar']

# Groupes de release connus à supprimer (en fin de chaîne qualité, avec ou sans tiret)
_RE_GROUP = re.compile(
    r'(?:\s*-|\s+)(?:RARBG|YIFY|YTS(?:\.BZ)?|SARTRE|FGT|EVO|NTb|HANDJOB)\s*$',
    re.IGNORECASE,
)
_RE_YTS_BRACKET = re.compile(r'\[YTS[^\]]*\]', re.IGNORECASE)
_RE_SERVICE     = re.compile(r'\b(?:VOSTFR|NETFLIX|Z2|MULTI)\b', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def clean_title(raw: str) -> str:
    """Convertit dots/underscores en espaces et nettoie les espaces multiples."""
    raw = raw.replace('.', ' ').replace('_', ' ')
    return re.sub(r'\s+', ' ', raw).strip()


_SMALL = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
          'on', 'at', 'to', 'by', 'in', 'of', 'up', 'as', 'so'}

def title_case(s: str) -> str:
    """Title case standard : petits mots en minuscule sauf en tête."""
    words = s.split()
    out = []
    for i, w in enumerate(words):
        out.append(w.capitalize() if (i == 0 or w.lower() not in _SMALL) else w.lower())
    return ' '.join(out)


def clean_quality(q: str) -> str:
    """Nettoie une chaîne qualité : supprime groupes de release, tags service, crochets résiduels."""
    q = _RE_YTS_BRACKET.sub('', q)
    q = _RE_GROUP.sub('', q)
    q = _RE_SERVICE.sub('', q)
    # Supprime les crochets isolés (ex. "[1080p] [WEBRip]" -> "1080p  WEBRip")
    q = re.sub(r'\[|\]', '', q)
    # Supprime les tirets traînants (ex. "AAC-" après suppression de "-[YTS.BZ]")
    q = re.sub(r'-\s*$', '', q)
    return re.sub(r'\s+', ' ', q).strip()


_RE_YEAR = re.compile(r'\b((?:19|20)\d{2})\b')


def parse_name(name: str):
    """
    Parse un nom (dossier ou fichier) → (title, year, quality).
    year peut être None si introuvable.
    """
    # Supprime l'extension connue
    stem = re.sub(
        r'\.(mkv|mp4|avi|mov|m4v|srt|sub|ass|nfo|txt)$', '', name, flags=re.IGNORECASE
    )

    # Pattern 1 : "Titre (Année) [Qualité]" — format canonique ou proche
    # Supporte plusieurs blocs entre crochets : "Titre (Année) [Q1] [Q2] [YTS.BZ]"
    m = re.match(
        r'^(.+?)\s*\(((?:19|20)\d{2})\)\s*(?:\[([^\]]*)\])?(?:\s*\[[^\]]*\])*\s*$',
        stem,
    )
    if m:
        return m.group(1).strip(), m.group(2), (m.group(3) or '').strip()

    # Pattern 2 : notation par points
    # Cas 2a : notation mixte — certains segments .séparés contiennent des espaces
    #   ex. "We All Loved Each Other So Much.Ettore Scola.1974.BluRay.HANDJOB"
    #   Le premier segment est le titre, les suivants sont directeur/qualité/groupe
    dot_parts = stem.split('.')
    if len(dot_parts) >= 3 and any(' ' in p for p in dot_parts):
        m2 = re.search(r'(?:^|\.)((?:19|20)\d{2})(?:\.|$)', stem)
        if m2:
            year = m2.group(1)
            # Tout ce qui précède le premier point est le titre
            first_dot = stem.index('.')
            year_pos  = stem.find(year)
            # Segments entre premier point et l'année = éléments à ignorer (directeur…)
            title = stem[:first_dot].strip()
            after = stem[year_pos + len(year):].lstrip('.')
            quality = clean_quality(after.replace('.', ' '))
            return title, year, quality

    # Cas 2b : notation purement par points "Titre.Titre.Année.Qualité-Groupe"
    # Heuristique : plus de points que d'espaces et au moins 3 points
    if stem.count('.') >= 3 and stem.count('.') >= stem.count(' '):
        m2 = re.search(r'\.((?:19|20)\d{2})\.', stem)
        if m2:
            year = m2.group(1)
            title = title_case(clean_title(stem[:m2.start()]))
            quality = clean_quality(stem[m2.end():].replace('.', ' '))
            return title, year, quality
        # Année sans points autour
        m2 = _RE_YEAR.search(stem)
        if m2:
            year = m2.group(1)
            title = title_case(clean_title(stem[:m2.start()].rstrip('.')))
            quality = clean_quality(stem[m2.end():].lstrip('.').replace('.', ' '))
            return title, year, quality

    # Pattern 3 : notation mixte/espaces "Titre Année Qualité..."
    m3 = _RE_YEAR.search(stem)
    if m3:
        year = m3.group(1)
        title = clean_title(stem[:m3.start()]).strip()
        quality = clean_quality(stem[m3.end():].strip())
        return title, year, quality

    return stem, None, ''


def parse_sub_lang(filename: str):
    """Extrait le code langue d'un nom de sous-titre (.lang.srt)."""
    stem = Path(filename).stem  # retire .srt
    for lang in sorted(KNOWN_LANGS, key=len, reverse=True):
        if stem.lower().endswith('.' + lang.lower()):
            return lang
    return None


# ---------------------------------------------------------------------------
# Noms canoniques
# ---------------------------------------------------------------------------

def canonical_folder(title: str, year: str) -> str:
    return f"{title} ({year})"

def canonical_video(title: str, year: str, quality: str, ext: str) -> str:
    if quality:
        return f"{title} ({year}) [{quality}]{ext}"
    return f"{title} ({year}){ext}"

def canonical_sub(title: str, year: str, lang: str) -> str:
    return f"{title} ({year}).{lang}.srt"

def canonical_nfo(title: str, year: str) -> str:
    return f"{title} ({year}).nfo"


# ---------------------------------------------------------------------------
# Organiseur principal
# ---------------------------------------------------------------------------

class FilmOrganizer:
    def __init__(self, library: Path, dry_run: bool):
        self.library  = library
        self.dry_run  = dry_run
        self.ops: list[str] = []
        self.warnings: list[str] = []

    # --- journalisation ---

    def _emit(self, msg: str):
        self.ops.append(msg)
        print(msg)

    def _warn(self, msg: str):
        full = f"  [!] {msg}"
        self.ops.append(full)
        self.warnings.append(full)
        print(full)

    # --- opérations fichier ---

    def _do_rename(self, src: Path, dst: Path):
        """Renomme src → dst (même dossier parent)."""
        if src == dst:
            return
        rel_src = src.relative_to(self.library)
        self._emit(f"  RENAME  {rel_src}  ->  {dst.name}")
        if not self.dry_run:
            if dst.exists():
                self._warn(f"Destination existe déjà, ignoré : {dst}")
                return
            src.rename(dst)

    def _do_move(self, src: Path, dst: Path):
        """Déplace src → dst (peut changer de dossier)."""
        if src == dst:
            return
        rel_src = src.relative_to(self.library)
        rel_dst = dst.relative_to(self.library)
        self._emit(f"  MOVE    {rel_src}  ->  {rel_dst}")
        if not self.dry_run:
            if dst.exists():
                self._warn(f"Destination existe déjà, ignoré : {dst}")
                return
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    def _do_mkdir(self, path: Path):
        self._emit(f"  MKDIR   {path.relative_to(self.library)}/")
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    # --- entrée principale ---

    def run(self):
        mode = "[DRY-RUN] " if self.dry_run else "[APPLY]   "
        self._emit(f"\n{'='*64}")
        self._emit(f"{mode}Bibliothèque : {self.library}")
        self._emit(f"{'='*64}")

        # 1. Fichiers vidéo lâches à la racine
        self._handle_root_loose_files()

        # 2. Dossiers à la racine
        for item in sorted(self.library.iterdir()):
            if item.name.startswith('.') or item.is_file():
                continue
            if re.search(r'\(Collection\)\s*$', item.name, re.IGNORECASE):
                self._handle_collection(item)
            else:
                self._handle_film_folder(item)

        self._write_log()
        n = len([o for o in self.ops if o.strip().startswith(('RENAME','MOVE','MKDIR'))])
        self._emit(f"\n{mode}{n} opération(s) planifiée(s).")
        if self.warnings:
            self._emit(f"  {len(self.warnings)} avertissement(s) — voir rename_log.txt")

    # --- fichiers lâches à la racine ---

    def _handle_root_loose_files(self):
        for item in sorted(self.library.iterdir()):
            if not item.is_file():
                continue
            if item.suffix.lower() not in VIDEO_EXTS:
                continue
            self._emit(f"\nFICHIER LÂCHE : {item.name}")
            title, year, quality = parse_name(item.name)
            if not year:
                self._warn(f"Impossible de déterminer l'année pour : {item.name}")
                continue
            folder_name = canonical_folder(title, year)
            new_folder  = self.library / folder_name
            new_file    = canonical_video(title, year, quality, item.suffix.lower())
            self._do_mkdir(new_folder)
            self._do_move(item, new_folder / new_file)

    # --- collection ---

    def _handle_collection(self, coll_folder: Path):
        self._emit(f"\nCOLLECTION : {coll_folder.name}/")
        for sub in sorted(coll_folder.iterdir()):
            if sub.is_dir():
                self._handle_film_folder(sub, inside_collection=True)

    # --- dossier film ---

    def _handle_film_folder(self, folder: Path, inside_collection: bool = False):
        self._emit(f"\n{'  ' if inside_collection else ''}DOSSIER : {folder.name}/")

        title, year, folder_quality = parse_name(folder.name)
        if not year:
            self._warn(f"Impossible de déterminer l'année pour : {folder.name}")
            return

        target_folder_name = canonical_folder(title, year)

        # Renomme le dossier si besoin
        if folder.name != target_folder_name:
            new_folder = folder.parent / target_folder_name
            self._do_rename(folder, new_folder)
            # En dry-run on continue avec l'ancien chemin (il n'a pas bougé)
            working_folder = new_folder if not self.dry_run else folder
        else:
            working_folder = folder

        self._handle_film_contents(working_folder, title, year, folder_quality)

    # --- contenu d'un dossier film ---

    def _handle_film_contents(self, folder: Path, title: str, year: str, fallback_quality: str):
        subs_dir = folder / 'Subs'

        for item in sorted(folder.iterdir()):
            if item.name.startswith('.'):
                continue

            # Sous-dossiers spéciaux
            if item.is_dir():
                lname = item.name.lower()
                if lname == 'extras':
                    self._emit(f"  EXTRAS      : {item.name}/ (contenu non modifié)")
                elif lname == 'featurettes':
                    self._emit(f"  FEATURETTES : {item.name}/ (contenu non modifié)")
                elif lname == 'subs':
                    self._handle_subs(item, title, year)
                else:
                    self._warn(f"Sous-dossier inconnu ignoré : {item.name}/")
                continue

            ext = item.suffix.lower()

            # Fichier vidéo principal
            if ext in VIDEO_EXTS:
                _, _, file_quality = parse_name(item.name)
                quality  = file_quality or fallback_quality
                new_name = canonical_video(title, year, quality, ext)
                self._do_rename(item, folder / new_name)

            # NFO à la racine du dossier → Subs/
            elif ext == '.nfo':
                if not self.dry_run:
                    subs_dir.mkdir(exist_ok=True)
                target = subs_dir / canonical_nfo(title, year)
                self._do_move(item, target)

            # info.txt → Subs/
            elif item.name.lower() == 'info.txt':
                if not self.dry_run:
                    subs_dir.mkdir(exist_ok=True)
                self._do_move(item, subs_dir / 'info.txt')

    # --- dossier Subs ---

    def _handle_subs(self, subs_dir: Path, title: str, year: str):
        for item in sorted(subs_dir.iterdir()):
            # Fichiers de timing (-7450ms.txt, etc.) : ignorés
            if item.name.startswith('-') or item.name.startswith('.'):
                continue

            ext = item.suffix.lower()

            if ext == '.srt':
                lang = parse_sub_lang(item.name)
                if lang:
                    new_name = canonical_sub(title, year, lang)
                    self._do_rename(item, subs_dir / new_name)
                else:
                    self._warn(f"Langue non détectée pour : {item.name}")

            elif ext == '.nfo':
                new_name = canonical_nfo(title, year)
                self._do_rename(item, subs_dir / new_name)

            # .txt autres (info.txt, etc.) : laissés en place
            elif ext == '.txt':
                pass

    # --- log ---

    def _write_log(self):
        log_path  = Path(__file__).parent / 'rename_log.txt'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        mode      = 'DRY-RUN' if self.dry_run else 'APPLIED'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*64}\n")
            f.write(f"{timestamp}  [{mode}]  {self.library}\n")
            f.write(f"{'='*64}\n")
            for line in self.ops:
                f.write(line + '\n')
        print(f"\nLog écrit dans : {log_path}")


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    lib_path = sys.argv[1]
    mode     = sys.argv[2]

    if not os.path.isdir(lib_path):
        print(f"Erreur : '{lib_path}' n'est pas un dossier.")
        sys.exit(1)

    if mode == '--dry-run':
        dry_run = True
    elif mode == '--run':
        dry_run = False
        print("ATTENTION : mode --run — les fichiers vont être modifiés.")
        answer = input("Confirmer ? (o/N) : ").strip().lower()
        if answer not in ('o', 'oui', 'y', 'yes'):
            print("Annulé.")
            sys.exit(0)
    elif mode == '--run-force':
        dry_run = False
    else:
        print(f"Mode inconnu : {mode}. Utiliser --dry-run ou --run")
        sys.exit(1)

    FilmOrganizer(Path(lib_path), dry_run).run()


if __name__ == '__main__':
    main()
