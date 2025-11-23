# Retraite Rustique (prototype cosy)

Petit prototype en `pygame` inspiré par le côté idle/relax de **Rusty's Retirement**. Il affiche une base de grille 6x6 mais s'étend automatiquement (voisinage "infini") quand on achète de nouvelles tuiles. Les arbres ont trois tailles, repoussent lentement, la poussière apparaît au hasard, et des événements (allié bûcheron, ennemi, arbre en or, fête, visite) peuvent se déclencher sur certaines tuiles.

## Lancer

```bash
pip install -r requirements.txt
python game.py
```

## Commandes principales

- **Barre du bas**: boutons emoji pour acheter, balayer, construire et choisir le bâtiment (cabane, atelier, tour de garde). Un bouton PC ouvre le panneau de vente.
- **Souris**: clic sur une tuile pour acheter (10 or) si elle est adjacente à une tuile possédée. Clic sur un arbre pour le couper (le bûcheron prend 5 à 10 s selon la taille), sur la poussière avec le balai pour nettoyer, ou pour placer un bâtiment sur une tuile possédée et libre.
- **C**: basculer directement l'outil balai/achat.
- **B**: dormir instantanément et repasser au matin.
- **P**: ouvrir le menu confort (ne met pas en pause mais permet d'ajuster la résolution à la souris).
- **Ctrl+S** ou **F5**: sauvegarder dans `savegame.json`.
- **Ctrl+L** ou **F9**: recharger la sauvegarde.

## Éléments de jeu

- **Ressources**: or, bois, poussière (poussière obtenue en nettoyant, bois en coupant les arbres — petit/moyen/grand arbre donnent 1/2/3 bois).
- **Machine à vendre (PC)**: clic pour ouvrir un dialogue de vente et confirmer la conversion bois (x4) et poussière (x2) en or avant d'acheter d'autres tuiles.
- **Lit**: clic pour passer la nuit et revenir à l'aube.
- **Poussière**: apparaît aléatoirement (max 3 tuiles à la fois). Nettoyer la retire et ajoute à l'inventaire.
- **Arbres**: repoussent progressivement sur les tuiles possédées avec un cycle de croissance (petit/moyen/grand) plus lent et une densité réduite. Ils cessent de pousser sur les tuiles où un bâtiment est construit.
- **Bûcherons**: se déplacent de manière fluide vers l'arbre mûr le plus proche et coupent pendant plusieurs secondes; un ami bûcheron peut apparaître via un événement, les ennemis sabotent mais peuvent être neutralisés automatiquement par les alliés.
- **Cycle jour/nuit**: 24 minutes pour une journée complète, avec saisons et météo changeantes appliquées à l'éclairage.
- **Sauvegarde**: `savegame.json` est chargé automatiquement au lancement et autosauvé régulièrement (et à la fermeture) avec la grille, l'inventaire, la météo, la résolution, les bûcherons, etc., pour partager la partie.
- **Construction**: cabane (habitat), atelier (production), tour de garde (esprit protecteur) coûtent bois+or et bloquent le repoussement des arbres autour.
- **Pixel art**: sprites maison façon Zelda-like (bûcheron allié/ennemi, arbres multi-tailles et dorés, poussière, PC, lit, constructions) et sols colorés par saison pour donner un rendu cosy immédiatement lisible.

Ce prototype reste compact et texturé par des rectangles/effets pixel saisonniers pour rester léger tout en posant les bases d'un système de tuiles extensible et scénarisable.
