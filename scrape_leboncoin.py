#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de scraping Leboncoin pour ajout automatique au CSV Destockgym
Usage: python3 scrape_leboncoin.py [URL]
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import sys
import time
from pathlib import Path
from datetime import datetime

# Configuration
CSV_FILE = "CSV-DESTOCKGYM-modif.csv"
URLS_CSV = "urls.csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
}


def scrape_with_requests(url):
    """Tente de scraper avec requests"""
    try:
        print("🔄 Tentative de scraping avec requests...")
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 403:
            print("❌ Erreur 403 - Passage à Selenium...")
            return None

        response.raise_for_status()
        return response.text

    except Exception as e:
        print(f"❌ Erreur requests: {e}")
        return None


def scrape_with_selenium(url):
    """Scrape avec Selenium en fallback"""
    try:
        print("🔄 Tentative de scraping avec Selenium...")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(f'user-agent={HEADERS["User-Agent"]}')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(url)

        # Attendre que la description se charge
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa-id="adview_description_container"]')))

        html = driver.page_source
        driver.quit()

        return html

    except Exception as e:
        print(f"❌ Erreur Selenium: {e}")
        return None


def extract_description_content(html):
    """Extrait la description de la page"""
    soup = BeautifulSoup(html, 'lxml')

    # Chercher le container de description
    desc_container = soup.find('div', {'data-qa-id': 'adview_description_container'})

    if not desc_container:
        print("❌ Container de description non trouvé")
        return None

    # Chercher le contenu dans la balise p ou div
    content_elem = desc_container.find('p', id='readme-content')
    if not content_elem:
        content_elem = desc_container.find('div')

    if content_elem:
        # Récupérer le texte en préservant les sauts de ligne
        description = content_elem.get_text(separator='\n', strip=True)
        return description

    return None


def clean_price(price_text):
    """Nettoie et convertit un prix en format numérique (ex: '1 456 €' -> '1456.0')"""
    if not price_text:
        return ''

    # Enlever tous les espaces (normal, nbsp \xa0, et espace insécable fin \u202f) et le symbole €
    price_cleaned = price_text.replace('\xa0', '').replace(' ', '').replace('€', '').replace('\u202f', '').strip()

    # Convertir en float puis retourner avec .0
    try:
        price_num = float(price_cleaned)
        return str(price_num)
    except ValueError:
        return ''


def extract_prices(html):
    """Extrait les prix (promo et régulier) de la page"""
    soup = BeautifulSoup(html, 'lxml')

    prices = {
        'tarif_promo': '',
        'tarif_regulier': ''
    }

    # 1. Chercher le TARIF PROMO
    # Méthode 1 : dans le container adview_price avec <p class="text-headline-1">
    price_container = soup.find('div', {'data-qa-id': 'adview_price'})

    if price_container:
        promo_elem = price_container.find('p', class_='text-headline-1')
        if promo_elem:
            price_text = promo_elem.get_text(strip=True)
            prices['tarif_promo'] = clean_price(price_text)

    # Méthode 2 (fallback) : chercher dans <div class="text-body-2 text-on-surface/dim-1 font-bold">
    if not prices['tarif_promo']:
        promo_elem_alt = soup.find('div', class_=lambda x: x and 'text-body-2' in x and 'font-bold' in x)
        if promo_elem_alt:
            price_text = promo_elem_alt.get_text(strip=True)
            # Enlever le " · " qui peut être à la fin
            price_text = price_text.split('·')[0].strip()
            prices['tarif_promo'] = clean_price(price_text)

    # 2. Chercher le TARIF RÉGULIER (prix barré)
    # Chercher <p role="deletion" class="...line-through...">
    regular_elem = soup.find('p', {'role': 'deletion', 'class': lambda x: x and 'line-through' in x})
    if regular_elem:
        price_text = regular_elem.get_text(strip=True)
        prices['tarif_regulier'] = clean_price(price_text)

    return prices


def parse_description_fields(description):
    """Parse les champs de la description"""
    fields = {
        'reference': '',
        'nom': '',
        'marque': '',
        'gamme': '',
        'type': '',
        'poids': '',
        'dimensions': '',
        'description_complete': description.replace('\n', '<br>')
    }

    lines = description.split('\n')

    for line in lines:
        line = line.strip()

        # Référence
        if line.lower().startswith('référence') or line.lower().startswith('reference'):
            match = re.search(r'(?:référence|reference)\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['reference'] = match.group(1).strip()

        # Nom
        elif line.lower().startswith('nom'):
            match = re.search(r'nom\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['nom'] = match.group(1).strip()

        # Marque
        elif line.lower().startswith('marque'):
            match = re.search(r'marque\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['marque'] = match.group(1).strip()

        # Gamme
        elif line.lower().startswith('gamme'):
            match = re.search(r'gamme\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['gamme'] = match.group(1).strip()

        # Type
        elif line.lower().startswith('type'):
            match = re.search(r'type\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['type'] = match.group(1).strip()

        # Poids
        elif 'poids' in line.lower():
            match = re.search(r'poids\s*:?\s*(\d+)\s*kg', line, re.IGNORECASE)
            if match:
                fields['poids'] = match.group(1) + 'Kg'

        # Dimensions
        elif 'dimension' in line.lower():
            match = re.search(r'dimension\w*\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                fields['dimensions'] = match.group(1).strip()

    return fields


def get_next_id(csv_path):
    """Obtient le prochain ID disponible"""
    try:
        df = pd.read_csv(csv_path)
        if len(df) > 0:
            max_id = df['ID'].max()
            return int(max_id) + 1
        return 1
    except Exception as e:
        print(f"❌ Erreur lecture CSV: {e}")
        return 1


def add_to_csv(csv_path, fields, prices):
    """Ajoute une nouvelle ligne au CSV"""
    try:
        # Obtenir le prochain ID
        next_id = get_next_id(csv_path)

        # Créer la nouvelle ligne
        new_row = {
            'ID': next_id,
            'Type': 'Simple',
            'UGS': fields['reference'],
            'Nom': fields['nom'],
            'Publié': 1,
            'Visibilité dans le catalogue': 'Visible',
            'Description': fields['description_complete'],
            'En stock ?': 1,
            'Stock': 1,
            'Poids (kg)': '',
            'Longueur (cm)': '',
            'Largeur (cm)': '',
            'Tarif promo': prices['tarif_promo'],
            'Tarif régulier': prices['tarif_regulier'],
            'Catégories': fields['type'],
            'Images': '',
            'Produits suggérés': '',
            'Ventes croisées': '',
            'Marques': fields['marque'],
            'Méta : dimensions': '',
            'Méta : poids_machine': '',
            'Méta : charges': '',
            'Méta : poids_max_de_l039utilisateur': '',
            'Méta : gamme_produit': fields['gamme'],
            'Méta : reference': fields['reference']
        }

        # Lire le CSV existant
        df = pd.read_csv(csv_path)

        # Ajouter la nouvelle ligne
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Sauvegarder
        df.to_csv(csv_path, index=False)

        print(f"\n✅ Ligne ajoutée | ID: {next_id} | UGS: {fields['reference']} | Nom: {fields['nom']} | Marque: {fields['marque']}")
        print(f"   💰 Prix: {prices['tarif_promo']} (Régulier: {prices['tarif_regulier']})")
        return True

    except Exception as e:
        print(f"❌ Erreur ajout CSV: {e}")
        return False


def scrape_single_url(url, csv_path):
    """Scrape une seule URL et ajoute au CSV"""
    print("=" * 60)
    print(f"🔗 URL: {url}\n")

    # 1. Scraper la page
    html = scrape_with_requests(url)

    if not html:
        html = scrape_with_selenium(url)

    if not html:
        print("❌ ÉCHEC: Impossible de récupérer la page")
        return False

    print("✅ Page récupérée")

    # 2. Extraire la description
    description = extract_description_content(html)

    if not description:
        print("❌ ÉCHEC: Description non trouvée")
        return False

    print("✅ Description extraite")
    print(f"\n📝 Description brute:\n{'-' * 60}\n{description}\n{'-' * 60}\n")

    # 3. Parser les champs
    fields = parse_description_fields(description)

    print("✅ Champs parsés:")
    for key, value in fields.items():
        if key != 'description_complete' and value:
            print(f"   - {key}: {value}")

    # 4. Extraire les prix
    prices = extract_prices(html)

    print("\n💰 Prix extraits:")
    print(f"   - Tarif promo: {prices['tarif_promo']}")
    print(f"   - Tarif régulier: {prices['tarif_regulier']}")

    # 5. Ajouter au CSV
    if not csv_path.exists():
        print(f"❌ ÉCHEC: Fichier {CSV_FILE} non trouvé")
        return False

    success = add_to_csv(csv_path, fields, prices)

    if success:
        print("\n🎉 MISSION ACCOMPLIE !")
        return True
    else:
        print("\n❌ ÉCHEC DE L'AJOUT AU CSV")
        return False


def read_urls_from_csv(csv_file):
    """Lit les URLs depuis le fichier CSV et retourne celles non scrapées"""
    try:
        df = pd.read_csv(csv_file)

        # Vérifier que la colonne 'url' existe
        if 'url' not in df.columns:
            print(f"❌ ERREUR: Le fichier {csv_file} doit contenir une colonne 'url'")
            return []

        # Ajouter les colonnes scraped et date_scraped si elles n'existent pas
        if 'scraped' not in df.columns:
            df['scraped'] = ''
        if 'date_scraped' not in df.columns:
            df['date_scraped'] = ''

        # Sauvegarder avec les nouvelles colonnes
        df.to_csv(csv_file, index=False)

        # Filtrer les URLs non scrapées
        urls_to_scrape = df[df['scraped'] != 'yes']['url'].tolist()

        return urls_to_scrape, df

    except FileNotFoundError:
        print(f"❌ ERREUR: Fichier {csv_file} non trouvé")
        return [], None
    except Exception as e:
        print(f"❌ ERREUR lors de la lecture du CSV: {e}")
        return [], None


def mark_url_as_scraped(csv_file, url):
    """Marque une URL comme scrapée dans le CSV"""
    try:
        df = pd.read_csv(csv_file, dtype=str)

        # Trouver l'index de l'URL
        mask = df['url'] == url

        # Mettre à jour les colonnes
        df.loc[mask, 'scraped'] = 'yes'
        df.loc[mask, 'date_scraped'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Sauvegarder
        df.to_csv(csv_file, index=False)

        return True
    except Exception as e:
        print(f"❌ ERREUR lors de la mise à jour du CSV: {e}")
        return False


def main():
    """Fonction principale"""
    # Vérifier si on utilise un fichier CSV ou des URLs en ligne de commande
    use_csv_file = False
    csv_file_path = URLS_CSV

    if len(sys.argv) >= 2 and (sys.argv[1] == '--file' or sys.argv[1] == '-f'):
        use_csv_file = True
        if len(sys.argv) >= 3:
            csv_file_path = sys.argv[2]

    # Mode fichier CSV
    if use_csv_file:
        print("=" * 60)
        print("🚀 SCRAPING LEBONCOIN → MODE FICHIER CSV")
        print("=" * 60)
        print(f"📂 Fichier: {csv_file_path}\n")

        urls_to_scrape, df = read_urls_from_csv(csv_file_path)

        if not urls_to_scrape:
            print("✅ Toutes les URLs ont déjà été scrapées !")
            return True

        print(f"📊 URLs à scraper: {len(urls_to_scrape)}\n")
        urls = urls_to_scrape

    # Mode ligne de commande
    else:
        if len(sys.argv) < 2:
            print("❌ ERREUR: URL(s) manquante(s)")
            print("\n📖 Usage:")
            print("   Mode fichier CSV : python3 scrape_leboncoin.py --file [urls.csv]")
            print("   Une URL          : python3 scrape_leboncoin.py <URL>")
            print("   Plusieurs URLs   : python3 scrape_leboncoin.py <URL1> <URL2> <URL3>")
            print("\n   Exemples:")
            print("   python3 scrape_leboncoin.py --file urls.csv")
            print("   python3 scrape_leboncoin.py https://www.leboncoin.fr/ad/sport_plein_air/3113864769")
            return False

        urls = sys.argv[1:]  # Toutes les URLs passées en arguments

    csv_path = Path(CSV_FILE)

    print("=" * 60)
    print("🚀 SCRAPING LEBONCOIN → AJOUT CSV AUTOMATIQUE")
    print("=" * 60)
    print(f"📊 Nombre d'URLs à scraper: {len(urls)}\n")

    # Compteurs de résultats
    success_count = 0
    fail_count = 0

    # Scraper chaque URL
    for i, url in enumerate(urls, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(urls)}] Traitement de l'URL...")

        result = scrape_single_url(url, csv_path)

        if result:
            success_count += 1

            # Marquer comme scrapée si on est en mode fichier CSV
            if use_csv_file:
                mark_url_as_scraped(csv_file_path, url)
                print(f"✅ URL marquée comme scrapée dans {csv_file_path}")
        else:
            fail_count += 1

        # Pause entre les requêtes pour éviter d'être bloqué
        if i < len(urls):
            print("\n⏳ Pause de 3 secondes avant la prochaine URL...")
            time.sleep(3)

    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 60)
    print(f"✅ Réussis: {success_count}")
    print(f"❌ Échecs: {fail_count}")
    print(f"📝 Total: {len(urls)}")
    print("=" * 60)

    return success_count > 0


if __name__ == "__main__":
    main()
