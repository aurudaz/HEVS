# Limites du modèle & pourquoi le dimensionnement devient trop grand

Ce document résume les principales limites du modèle Ronquoz 21 et explique pourquoi certains résultats (notamment le stockage électrique) deviennent irréalistes à grande échelle.

## Limites principales du modèle
- **Thermique basée sur SIA 380/1** : les besoins de chauffage/ECS sont calculés à partir de valeurs normatives et de facteurs d’enveloppe moyens. Il n’y a pas de simulation thermodynamique détaillée (infiltration, apports solaires, rendement systèmes, etc.).
- **Météo unique** : un seul jeu de données météo est utilisé (année de référence) sans scénarios climatiques ni variabilité interannuelle.
- **Inertie et foisonnement simplifiés** : l’inertie est modélisée par un lissage exponentiel, et le foisonnement est appliqué via des facteurs fixes par affectation.
- **Aucune perte réseau** : les pertes thermiques dans les conduites et la consommation des pompes ne sont pas modélisées.
- **Hydraulique linéarisée** : le dimensionnement des diamètres est basé sur une contrainte simplifiée, sans modèle hydraulique complet (pertes quadratiques, vannes, pompes).
- **Photovoltaïque simplifié** : production PV via un profil horaire unique (PVGIS), sans ombrage, sans dégradation ni variabilité d’orientation fine.
- **Électricité par profils types** : les charges électriques utilisent des profils standards, sans modéliser la diversité réelle des usages (efficacité, appareillage, comportement).
- **Stockage supposé idéal** : la capacité batterie est déduite du surplus cumulé, sans rendement, dégradation ni contraintes de puissance/charge.
- **Coûts indicatifs** : CAPEX réseau et batteries sont des ordres de grandeur, pas un devis détaillé.

## Pourquoi le stockage “devient trop grand”
Le scénario “100% autoconsommation” impose de stocker l’excédent PV d’été pour le restituer en hiver. Cela revient à un **stockage saisonnier** en énergie électrique, ce qui dépasse les capacités réalistes des batteries chimiques :

- La capacité nécessaire est de plusieurs **GWh** (ordre de grandeur d’un réseau régional).
- Un tel stockage coûterait **des centaines de millions de CHF** et nécessiterait des surfaces dédiées importantes.
- Les batteries ne sont pas adaptées au stockage saisonnier (rendement, auto‑décharge, durée de vie).

**Conclusion :** le “100% autoconsommation” est un cas théorique qui montre l’ordre de grandeur, mais il n’est pas réaliste sans solutions alternatives (stockage thermique, effacement de charge, interconnexion réseau, etc.).

## Références utilisées
- SIA 380/1 – Besoins de chaleur pour le chauffage et l’ECS.
- SIA 2024 – Données d’exploitation et profils horaires.
- SIA 380/4 – Énergie électrique dans les bâtiments.
- OFEN/SFOE – seuils de densité énergétique pour réseaux de chaleur.
