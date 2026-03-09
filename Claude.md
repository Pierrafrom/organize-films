# Vidéothèque Organizer

## Objectif
Script Python pour renommer et organiser automatiquement une bibliothèque de films.

## Conventions de nommage (à respecter strictement)

### Structure des dossiers
```
Films/
└── Titre du Film (Année)/
    ├── Titre du Film (Année) [Qualité].mkv
    └── Subs/
            Titre du Film (Année).fr.srt
            Titre du Film (Année).en.srt
            Titre du Film (Année).nfo
```

### Cas spéciaux
- **Collections** : `Titre (Collection)/Titre (Année)/...`
- **Extras** : sous-dossier `Extras/` dans le dossier du film
- **Featurettes** : sous-dossier `Featurettes/` dans le dossier du film

### Règles
- Toujours un dry-run d'abord (--dry-run flag)
- Logger toutes les opérations dans rename_log.txt
- Ne jamais supprimer de fichiers, seulement déplacer/renommer
- Conserver les fichiers .nfo dans Subs/
- Langues reconnues : .fr .en .pt-BR .es
- le script doit prendre en paramètre le chemin de la bibliothèque à organiser

## Stack
- Python 3, stdlib uniquement (pas de dépendances externes)
- Compatible Windows (chemins avec os.path)

## Conventions Git & GitHub

### Structure de branches
- main : production stable uniquement
- develop : intégration
- feature/* : nouvelles fonctionnalités
- fix/* : corrections

### README template
Toujours inclure : description, badges, installation, usage, structure du projet, licence

### Commits
Utiliser Conventional Commits : feat:, fix:, docs:, chore:, refactor: