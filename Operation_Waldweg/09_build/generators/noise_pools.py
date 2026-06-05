#!/usr/bin/env python3
# =====================================================================
# noise_pools.py  —  kuratierte, lokalisierte Noise-Bibliotheken (Schritt 2)
# ---------------------------------------------------------------------
# Liefert plausible Alltags-Noise-Bausteine, aus denen der seed-RNG je Fall
# eine individuelle Auswahl zieht (caseforge_rng.sample). Nur NOISE — keine
# fallrelevanten Inhalte. Sprachabhaengig (de/en, Fallback de).
# =====================================================================

WEB = {
    "de": [
        ("https://www.tagesschau.de/", "tagesschau.de - Nachrichten"),
        ("https://www.wetter.com/", "Wetter Deutschland"),
        ("https://www.chefkoch.de/", "Chefkoch - Rezepte"),
        ("https://www.kicker.de/", "kicker - Fussball"),
        ("https://www.amazon.de/", "Amazon.de"),
        ("https://www.ebay-kleinanzeigen.de/", "Kleinanzeigen"),
        ("https://www.youtube.com/", "YouTube"),
        ("https://www.dm.de/", "dm-drogerie markt"),
        ("https://www.bahn.de/", "Deutsche Bahn"),
        ("https://www.google.com/search?q=oeffnungszeiten+baumarkt", "oeffnungszeiten baumarkt"),
        ("https://www.immobilienscout24.de/", "ImmoScout24"),
        ("https://www.idealo.de/", "Preisvergleich idealo"),
    ],
    "en": [
        ("https://www.bbc.com/news", "BBC News"),
        ("https://weather.com/", "Weather"),
        ("https://www.allrecipes.com/", "Allrecipes"),
        ("https://www.espn.com/", "ESPN"),
        ("https://www.amazon.com/", "Amazon.com"),
        ("https://www.reddit.com/", "Reddit"),
        ("https://www.youtube.com/", "YouTube"),
        ("https://www.google.com/search?q=hardware+store+near+me", "hardware store near me"),
        ("https://www.zillow.com/", "Zillow"),
        ("https://www.ebay.com/", "eBay"),
    ],
}

DOCS = {
    "de": [
        ("Einkaufsliste.txt", "txt", "Einkaufsliste"),
        ("Rezept_Lasagne.pdf", "pdf", "Rezept"),
        ("Versicherung_Police.pdf", "pdf", "Versicherungsunterlagen"),
        ("Urlaub_Packliste.txt", "txt", "Packliste"),
        ("Haushaltsbuch.csv", "csv", "Haushaltsbuch"),
        ("Vereinsbeitrag_2026.pdf", "pdf", "Vereinsbeitrag"),
        ("Gartenplan.txt", "txt", "Gartenplan"),
        ("Kontoauszug_Export.csv", "csv", "Kontoauszug"),
    ],
    "en": [
        ("ShoppingList.txt", "txt", "Shopping list"),
        ("Recipe_Lasagne.pdf", "pdf", "Recipe"),
        ("Insurance_Policy.pdf", "pdf", "Insurance documents"),
        ("Vacation_Packing.txt", "txt", "Packing list"),
        ("Budget.csv", "csv", "Household budget"),
        ("Statement_Export.csv", "csv", "Bank statement"),
    ],
}

SMS = {
    "de": [
        "Bist du heute Abend zuhause?", "Kannst du Brot mitbringen?",
        "Termin beim Zahnarzt verschoben auf Donnerstag.", "Danke fuer gestern :)",
        "Bin 10 Min spaeter.", "Paket ist angekommen.", "Wie war dein Tag?",
        "Treffen wir uns um 18 Uhr?", "Hast du den Schluessel?", "Gute Besserung!",
    ],
    "en": [
        "Are you home tonight?", "Can you grab some bread?",
        "Dentist moved to Thursday.", "Thanks for yesterday :)",
        "Running 10 min late.", "Parcel arrived.", "How was your day?",
        "Meet at 6?", "Do you have the key?", "Get well soon!",
    ],
}

CONTACTS = {
    "de": ["Mama", "Papa", "Lukas Berger", "Sandra Wolf", "Dr. Hoffmann",
           "Pizzeria Bella", "Werkstatt", "Apotheke", "Kita Sonnenschein"],
    "en": ["Mum", "Dad", "Lucas Brown", "Sandra Wolf", "Dr. Carter",
           "Pizza Place", "Garage", "Pharmacy", "Daycare"],
}

# Generische Noise-Apps (Bundle-IDs/Pakete) fuer zufaellige Sandbox-Auswahl
APPS = {
    "ios": ["com.spotify.client", "com.netflix.Netflix", "com.google.Maps",
            "com.amazon.Amazon", "com.pinterest", "com.zhiliaoapp.musically",
            "com.linkedin.LinkedIn", "net.whatsapp.WhatsApp", "com.toyopagroup.picaboo",
            "com.google.Gmail", "com.apple.mobilenotes", "com.king.candycrushsaga"],
    "android": ["com.spotify.music", "com.netflix.mediaclient", "com.google.android.apps.maps",
                "com.amazon.mShop.android.shopping", "com.pinterest", "com.zhiliaoapp.musically",
                "com.linkedin.android", "com.whatsapp", "com.instagram.android",
                "com.google.android.gm", "com.dropbox.android", "com.spotify.lite"],
}


def web(lang):
    return WEB.get(lang, WEB["de"])


def docs(lang):
    return DOCS.get(lang, DOCS["de"])


def sms(lang):
    return SMS.get(lang, SMS["de"])


def contacts(lang):
    return CONTACTS.get(lang, CONTACTS["de"])


def apps(platform):
    return APPS.get(platform, [])
