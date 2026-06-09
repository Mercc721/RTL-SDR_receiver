# RTL-SDR FM Radio 

Une radio FM qui tourne sur votre ordinateur, sans abonnement, sans streaming. Vous branchez une petite clé USB, vous lancez le script, et vous captez les vraies ondes radio qui passent dans l'air autour de vous — exactement comme une radio physique, sauf que tout le traitement du signal se fait dans Python.

---

## Le contexte

Une clé RTL-SDR, c'est un dongle USB vendu à la base pour regarder la TNT sur PC. Des bidouilleurs ont découvert qu'on pouvait le détourner pour capter à peu près n'importe quelle fréquence entre 25 MHz et 1.75 GHz. Ce projet s'en sert pour écouter la FM (87.5 – 108 MHz), mais ça marche aussi sur les fréquences VHF marine jusqu'à 170 MHz.

L'interface ressemble à une vraie radio : écran LCD vert, boutons ronds, pavé numérique pour entrer une fréquence à la main.

---

## Ce qu'il vous faut

Une clé RTL-SDR (RTL2832U) et une antenne 
Ensuite :
**Logiciel**
- la commande rtl_tcp dans un terminal afin de chercher la clé RTL-SDR 
- Python 3 dans un autre terminal 
- Python 3.13.13
```bash
pip install pyrtlsdr numpy scipy sounddevice
```

Sur Mac, les drivers USB en plus :

```bash
brew install librtlsdr
```
- installation du logiciel zadig et télécharger le driver approprié 
---

## Lancer

```bash
git clone https://github.com/Mercc721/RTL-SDR_receiver.git
cd RTL-SDR_receiver
python main.py
```

Branchez la clé avant de lancer.

---

## Utilisation

- **PWR** pour allumer. L'écran affiche `SDR CONNECT...` pendant 1-2 secondes le temps que la clé s'initialise.
- **+1 / +.1 / -.1 / -1** pour naviguer entre les stations.
- Pavé numérique + **E** pour entrer une fréquence directement : `1017` → 101.7 MHz, `956` → 95.6 MHz.
- **FM** remet à 100.0 MHz.
- **PWR** à nouveau pour éteindre proprement.

---

## Structure du code

```
RTL-SDR_receiver/
├── main.py            # Point d'entrée
├── config.py          # Fréquences, couleurs, taux d'échantillonnage
├── radio_engine.py    # Lit les données brutes depuis la clé USB
├── audio_worker.py    # Démodule le signal et envoie le son à la carte son
└── sdr_fm_radio.py    # Interface graphique
```

`radio_engine` et `audio_worker` tournent dans des threads séparés. La clé produit les données, un buffer les stocke, le démodulateur les consomme — les trois sans jamais se bloquer mutuellement.

---

## Comment ça marche

La clé envoie des échantillons IQ bruts — des nombres complexes qui encodent le signal radio. Pour en tirer du son :

1. Filtre passe-bas sur le signal IQ pour isoler la station et rejeter les voisines
2. Discriminateur de phase `angle(s[n] × conj(s[n-1]))` — c'est la démodulation FM
3. Rééchantillonnage de 1.152 MHz vers 48 kHz pour la carte son
4. Filtres audio : passe-bas 15 kHz + dé-emphase 75 µs (norme FM) + coupe-bas 30 Hz
5. AGC pour équilibrer le volume automatiquement selon la puissance de la station

---

## Versions

| Tag | 
|-----|
| V0  | 
| V1  | 

---

## Problèmes courants

**`SDR INIT ERROR`** — La clé n'est pas reconnue. Vérifiez qu'elle est branchée et que `librtlsdr` est installé. Sur Mac, un driver Apple peut entrer en conflit : `sudo kextunload -b com.apple.driver.usb.cdc.acm`
