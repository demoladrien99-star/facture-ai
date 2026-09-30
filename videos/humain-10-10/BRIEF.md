---
workflow: faceless-explainer
flow: automation
storyboard: no
message: "En 50 secondes tu sais exactement quoi faire pour tout changer."
destination: tiktok
aspect: 1080x1920
language: fr
audience: "Garçons 15-20 ans, sport et self-improvement"
length: 57s
angle: listicle
voice: piper fr_FR-tom-medium (masculine, local, vérifiée par ASR)
---

## Intent

Vidéo TikTok verticale « Deviens un humain 10/10 » : physique + mindset, ton coach
direct et cash. Esthétique dark, épurée, percutante — typographie cinétique, chiffres
animés, icônes minimalistes au trait, texte révélé par masque, coupes sèches sur le beat.

## Customizations

- Palette : fond `#0A0A0A`, texte `#FFFFFF`, accent `#FF2D2D` uniquement sur mots-clés et chiffres.
- Inter Black (titres) / Inter Medium (texte), fichiers locaux `assets/fonts/`.
- Composants reproduits à la main (façon 21st.dev) dans `assets/hf10.js` : Text Rotate
  (S01, S05), Number Ticker (S02, S04), Animated List (S03, S05), Border Beam (S02, S06),
  Shimmer Button (S07).
- Sans musique (demande utilisateur) : voix off + SFX (whoosh / impact / pop / confirm) synthétisés localement. La grille 110 BPM reste la base du rythme des coupes.

## Notes

- Pas d'emoji, pas de dégradé coloré, pas de glassmorphism, pas de 3D.
- « Plus que 99% de tes potes » remplacé par « 12 de plus que tes potes. » (règle : aucun chiffre inventé).
- Voix off : texte du script, avec trois ajustements de diction pour la voix seulement (l'écran ne change pas) :
  « bodybuilder » → prononcé « bodibildeur », « Lis dix pages » → « Lire dix pages »,
  « Huit heures, pas sept » → « Huit heures, et pas sept » (sinon entendu « passée »).
