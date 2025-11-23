# Retraite Rustique (prototype cosy)

Petit prototype en `pygame` inspiré par le côté idle/relax de **Rusty's Retirement**. Il affiche une grille 6x6 (36 tuiles) avec arbres repoussant, poussière à nettoyer, météo/saisons et un bûcheron autonome.

## Lancer

```bash
pip install -r requirements.txt
python game.py
```

## Commandes principales

- **Souris**: clic sur une tuile pour acheter (10 or) si elle est adjacente à une tuile possédée. Clic sur un arbre pour le couper, sur la poussière avec le balai pour nettoyer.
- **C**: basculer l'outil balai.
- **B**: dormir instantanément et repasser au matin.
- **Ctrl+S** ou **F5**: sauvegarder dans `savegame.json`.
- **Ctrl+L** ou **F9**: recharger la sauvegarde.
- **[ / ]**: diminuer/augmenter la largeur de la fenêtre.
- **; / '**: diminuer/augmenter la hauteur de la fenêtre.

## Éléments de jeu

- **Ressources**: or, bois, poussière (poussière obtenue en nettoyant, bois en coupant les arbres).
- **Machine à vendre (PC)**: clic pour convertir bois (4 or) et poussière (2 or) en or et acheter de nouvelles tuiles adjacentes.
- **Lit**: clic pour passer la nuit et revenir à l'aube.
- **Poussière**: apparaît aléatoirement (max 3 tuiles à la fois). Nettoyer la retire et ajoute à l'inventaire.
- **Arbres**: repoussent progressivement sur les tuiles possédées; le bûcheron se déplace automatiquement vers l'arbre mûr le plus proche pour le couper.
- **Cycle jour/nuit**: 24 minutes pour une journée complète, avec saisons et météo changeantes appliquées à l'éclairage.
- **Sauvegarde**: `savegame.json` contient la grille, l'inventaire, la météo, la résolution, etc., pour partager la partie.

Ce prototype reste compact et texturé par des couleurs/rectangles pour rester léger tout en posant les bases d'un système de tuiles extensible.
