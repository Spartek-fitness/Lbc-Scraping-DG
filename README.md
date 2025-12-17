# Documentation - Script de scraping Leboncoin (macOS)

## Prérequis

Le dossier `Destockgym-script` doit contenir :
- `scrape_leboncoin.py` (le script)
- `CSV-DESTOCKGYM-modif.csv` (votre fichier CSV)

## Installation (première fois uniquement)

### Étape 1 : Installer Python

1. Ouvrir le Terminal
2. Installer Homebrew (si pas déjà installé) :
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Installer Python :
   ```bash
   brew install python
   ```
4. Vérifier l'installation :
   ```bash
   python3 --version
   ```

### Étape 2 : Installer les dépendances Python

1. Ouvrir le Terminal
2. Aller dans le dossier Destockgym-script :
   ```bash
   cd /chemin/vers/Destockgym-script
   ```
3. Installer les packages nécessaires :
   ```bash
   pip3 install --break-system-packages requests beautifulsoup4 lxml pandas selenium webdriver-manager
   ```

## Utilisation

Le script propose 2 modes d'utilisation :

### Mode 1 : Fichier CSV (RECOMMANDÉ pour plus de 20 URLs)

1. Créer un fichier `urls.csv` avec une colonne "url" :
   ```csv
   url,scraped,date_scraped
   https://www.leboncoin.fr/ad/blabla/3113819301,,
   https://www.leboncoin.fr/ad/blabla/3113794139,,
   https://www.leboncoin.fr/ad/blabla/3113569466,,
   ```

2. Ouvrir le Terminal et aller dans le dossier :
   ```bash
   cd /chemin/vers/Destockgym-script
   ```

3. Lancer le script :
   ```bash
   python3 scrape_leboncoin.py --file urls.csv
   ```

Avantages du mode fichier CSV :
- Le script marque automatiquement les URLs scrapées
- Vous pouvez relancer le script, il skip les URLs déjà faites
- Parfait pour 395 URLs : scraper en plusieurs sessions
- Reprise automatique en cas d'interruption
- Colonne "date_scraped" pour tracer l'historique

### Mode 2 : Ligne de commande (pour 1 à 20 URLs)

1. Ouvrir le Terminal et aller dans le dossier :
   ```bash
   cd /chemin/vers/Destockgym-script
   ```

2. Lancer le script avec une ou plusieurs URLs :

   **Une seule URL :**
   ```bash
   python3 scrape_leboncoin.py https://www.leboncoin.fr/ad/sport_plein_air/XXXXXXX
   ```

   **Plusieurs URLs (séparées par des espaces) :**
   ```bash
   python3 scrape_leboncoin.py URL1 URL2 URL3 URL4 URL5
   ```

### Exemples concrets

**Scraper une seule annonce :**
```bash
python3 scrape_leboncoin.py https://www.monurl.com
```

**Scraper 5 annonces d'un coup :**
```bash
python3 scrape_leboncoin.py \
  https://www.monurl.com \
  https://www.monurl.com \
  https://www.monurl.com \
  https://www.monurl.com \
  https://www.monurl.com \
  https://www.monurl.com \
  
```

Note : Le `\` permet de continuer la commande sur plusieurs lignes pour plus de lisibilité. Vous pouvez aussi tout mettre sur une seule ligne.

### Ce que fait le script

Le script va automatiquement :
1. Scraper chaque annonce Leboncoin (une par une)
2. Extraire les informations (Référence, Nom, Marque, Prix, Description, etc.)
3. Ajouter une nouvelle ligne dans le CSV pour chaque annonce
4. Faire une pause de 2 secondes entre chaque annonce (pour éviter d'être bloqué)
5. Afficher un résumé final avec le nombre de réussites et d'échecs

## Informations extraites automatiquement

Le script récupère de l'annonce :
- Référence produit
- Nom du produit
- Marque
- Gamme
- Type/Catégorie
- Description complète (avec formatage)
- Tarif promo (format numérique, ex: 490.0)
- Tarif régulier (format numérique, ex: 1456.0)

## Dépannage

**Erreur "command not found: python3" :**
- Python n'est pas installé
- Installer Python avec Homebrew (voir Étape 1)

**Erreur "No module named 'requests'" :**
- Les dépendances ne sont pas installées
- Lancer la commande pip3 install de l'Étape 2

**Erreur "FileNotFoundError: CSV-DESTOCKGYM-modif.csv" :**
- Le fichier CSV n'est pas dans le même dossier que le script
- Vérifier que le CSV est bien dans le dossier Destockgym-script

**Erreur "externally-managed-environment" :**
- Ne pas oublier le flag --break-system-packages dans la commande pip3 install

## Vérifications avant utilisation

1. Python est installé :
   ```bash
   python3 --version
   ```

2. Les packages sont installés :
   ```bash
   pip3 list | grep requests
   ```

3. Vous êtes dans le bon dossier :
   ```bash
   pwd
   ls -l
   ```
   Vous devez voir scrape_leboncoin.py et CSV-DESTOCKGYM-modif.csv

4. Le fichier CSV existe :
   ```bash
   ls CSV-DESTOCKGYM-modif.csv
   ```
