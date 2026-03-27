# AGENTS.md

## Git workflow
- Toujours committer les modifications réalisées.
- Faire des commits intermédiaires réguliers pendant le travail, dès qu'une étape est stable et vérifiable.
- Préférer plusieurs petits commits cohérents plutôt qu'un gros commit final.
- Toujours pousser (`git push`) juste après le commit.

## Versioning
- Maintenir une version applicative au format `MAJOR.MINOR.PATCH` dans le fichier `VERSION`.
- A chaque modification livrée (commit + push), incrémenter uniquement `PATCH`.
- Afficher la version courante dans l'UI à côté de `Site inauguré le ...`.
