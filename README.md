# organize-films

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)]()

Script Python pour renommer et organiser automatiquement une bibliothèque de films selon une convention stricte. Fonctionne en **dry-run** par défaut — aucune modification sans confirmation.

## Structure cible

```
Films/
└── Titre du Film (Année)/
    ├── Titre du Film (Année) [Qualité].mkv
    └── Subs/
        ├── Titre du Film (Année).fr.srt
        ├── Titre du Film (Année).en.srt
        └── Titre du Film (Année).nfo
```

Collections, `Extras/` et `Featurettes/` sont gérés automatiquement.

## Installation

Aucune dépendance externe — Python 3.8+ uniquement.

```bash
git clone https://github.com/Pierrafrom/organize-films.git
cd organize-films
```

## Usage

```bash
# Aperçu sans modification
python organize_films.py /path/to/library --dry-run

# Appliquer avec confirmation
python organize_films.py /path/to/library --run

# Appliquer sans confirmation
python organize_films.py /path/to/library --run-force
```

**Windows** — double-cliquer sur `organize.bat` dans le dossier à organiser pour un dry-run interactif.

Toutes les opérations sont journalisées dans `rename_log.txt`.

## Fonctionnalités

- Renommage des dossiers et fichiers vidéo au format canonique
- Détection automatique du titre, de l'année et de la qualité (BluRay, WEBRip, 1080p…)
- Suppression des tags de release (YIFY, RARBG, YTS…)
- Gestion des sous-titres multilingues (`.fr`, `.en`, `.es`, `.pt-BR`…)
- Déplacement des `.nfo` dans `Subs/`
- Dossiers `Extras/` et `Featurettes/` préservés intacts
- Jamais de suppression de fichiers

## Licence

MIT
