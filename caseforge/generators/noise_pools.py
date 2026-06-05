#!/usr/bin/env python3
# =====================================================================
# noise_pools.py  —  kuratierte, lokalisierte Noise-Bibliotheken (Schritt 2)
# ---------------------------------------------------------------------
# Liefert plausible Alltags-Noise-Bausteine, aus denen der seed-RNG je Fall
# eine individuelle Auswahl zieht (caseforge_rng.sample). Nur NOISE — keine
# fallrelevanten Inhalte. Sprachabhaengig (de/en/fr/es/tr, Fallback de).
#
# Die Pools sind bewusst gross gewaehlt, damit auch grosse Faelle (scope XL)
# eine abwechslungsreiche, nicht repetitive Auswahl erhalten.
# =====================================================================

# ---------------------------------------------------------------------
# Web-Verlauf  (url, title)
# ---------------------------------------------------------------------
WEB = {
    "de": [
        ("https://www.tagesschau.de/", "tagesschau.de - Nachrichten"),
        ("https://www.wetter.com/wetter_aktuell/", "Wetter Deutschland - wetter.com"),
        ("https://www.chefkoch.de/rezepte/", "Rezepte - Chefkoch"),
        ("https://www.kicker.de/bundesliga/spieltag", "Bundesliga Spieltag - kicker"),
        ("https://www.amazon.de/gp/bestsellers", "Bestseller - Amazon.de"),
        ("https://www.kleinanzeigen.de/s-fahrrad/", "Fahrrad - Kleinanzeigen"),
        ("https://www.youtube.com/feed/trending", "Trends - YouTube"),
        ("https://www.dm.de/angebote", "Angebote - dm"),
        ("https://www.bahn.de/buchung/start", "Reiseauskunft - Deutsche Bahn"),
        ("https://www.google.com/search?q=oeffnungszeiten+baumarkt", "oeffnungszeiten baumarkt - Suche"),
        ("https://www.immobilienscout24.de/wohnung-mieten", "Wohnung mieten - ImmoScout24"),
        ("https://www.idealo.de/preisvergleich/", "Preisvergleich - idealo"),
        ("https://www.spiegel.de/", "DER SPIEGEL - Nachrichten"),
        ("https://www.zdf.de/sport", "Sport - ZDF"),
        ("https://www.lieferando.de/", "Essen bestellen - Lieferando"),
        ("https://www.netflix.com/browse", "Startseite - Netflix"),
        ("https://www.google.com/maps/dir/", "Routenplaner - Google Maps"),
        ("https://www.apotheken-umschau.de/", "Apotheken Umschau"),
        ("https://www.check24.de/strom/", "Stromvergleich - CHECK24"),
        ("https://www.otto.de/sale/", "SALE - OTTO"),
        ("https://www.google.com/search?q=stau+a8+heute", "stau a8 heute - Suche"),
        ("https://www.mediamarkt.de/de/category/notebooks", "Notebooks - MediaMarkt"),
        ("https://www.dhl.de/de/privatkunden/sendungsverfolgung.html", "Sendungsverfolgung - DHL"),
        ("https://www.tripadvisor.de/", "Reisebewertungen - Tripadvisor"),
        ("https://www.fahrplanauskunft.vvs.de/", "Fahrplan - VVS Stuttgart"),
        ("https://www.thalia.de/buecher/", "Buecher - Thalia"),
        ("https://www.google.com/search?q=kino+programm+heute", "kino programm heute - Suche"),
        ("https://www.wikipedia.org/wiki/Schwarzwald", "Schwarzwald - Wikipedia"),
        ("https://www. recipes", "Kochbuch online"),
        ("https://www.fitnessstudio-finder.de/", "Fitnessstudio in der Naehe"),
    ],
    "en": [
        ("https://www.bbc.com/news", "BBC News"),
        ("https://weather.com/today", "Today's Weather - weather.com"),
        ("https://www.allrecipes.com/recipes/", "Recipes - Allrecipes"),
        ("https://www.espn.com/soccer/", "Soccer - ESPN"),
        ("https://www.amazon.com/gp/bestsellers", "Best Sellers - Amazon"),
        ("https://www.reddit.com/r/all/", "Reddit"),
        ("https://www.youtube.com/feed/trending", "Trending - YouTube"),
        ("https://www.google.com/search?q=hardware+store+near+me", "hardware store near me - Search"),
        ("https://www.zillow.com/homes/for_rent/", "Apartments for rent - Zillow"),
        ("https://www.ebay.com/deals", "Deals - eBay"),
        ("https://www.netflix.com/browse", "Home - Netflix"),
        ("https://www.google.com/maps/dir/", "Directions - Google Maps"),
        ("https://www.theguardian.com/", "The Guardian"),
        ("https://www.nytimes.com/", "The New York Times"),
        ("https://www.ubereats.com/", "Order food - Uber Eats"),
        ("https://www.cnn.com/", "CNN"),
        ("https://www.tripadvisor.com/", "Tripadvisor"),
        ("https://www.walmart.com/", "Walmart"),
        ("https://www.google.com/search?q=traffic+i95+now", "traffic i95 now - Search"),
        ("https://www.bestbuy.com/laptops", "Laptops - Best Buy"),
        ("https://www.fedex.com/tracking", "Tracking - FedEx"),
        ("https://en.wikipedia.org/wiki/Black_Forest", "Black Forest - Wikipedia"),
        ("https://www.spotify.com/", "Spotify"),
        ("https://www.google.com/search?q=movie+times+today", "movie times today - Search"),
        ("https://www.indeed.com/jobs", "Jobs - Indeed"),
        ("https://www.booking.com/", "Booking.com"),
        ("https://www.healthline.com/", "Healthline"),
        ("https://www.target.com/", "Target"),
    ],
    "fr": [
        ("https://www.lemonde.fr/", "Le Monde - Actualites"),
        ("https://www.meteofrance.com/", "Meteo-France"),
        ("https://www.marmiton.org/recettes/", "Recettes - Marmiton"),
        ("https://www.lequipe.fr/Football/", "Football - L'Equipe"),
        ("https://www.amazon.fr/gp/bestsellers", "Meilleures ventes - Amazon.fr"),
        ("https://www.leboncoin.fr/", "Leboncoin"),
        ("https://www.youtube.com/feed/trending", "Tendances - YouTube"),
        ("https://www.sncf-connect.com/", "Billets de train - SNCF Connect"),
        ("https://www.google.com/search?q=horaires+pharmacie", "horaires pharmacie - Recherche"),
        ("https://www.seloger.com/locations/", "Locations - SeLoger"),
        ("https://www.fnac.com/", "Fnac"),
        ("https://www.netflix.com/browse", "Accueil - Netflix"),
        ("https://www.bfmtv.com/", "BFM TV"),
        ("https://www.deliveroo.fr/", "Commander - Deliveroo"),
        ("https://www.darty.com/nav/achat/informatique/", "Informatique - Darty"),
        ("https://www.google.com/maps/dir/", "Itineraire - Google Maps"),
        ("https://fr.wikipedia.org/wiki/Foret-Noire", "Foret-Noire - Wikipedia"),
        ("https://www.cdiscount.com/", "Cdiscount"),
    ],
    "es": [
        ("https://www.elpais.com/", "El Pais - Noticias"),
        ("https://www.eltiempo.es/", "El Tiempo - Meteorologia"),
        ("https://www.recetasgratis.net/", "Recetas - RecetasGratis"),
        ("https://www.marca.com/futbol/", "Futbol - Marca"),
        ("https://www.amazon.es/gp/bestsellers", "Mas vendidos - Amazon.es"),
        ("https://www.milanuncios.com/", "Milanuncios"),
        ("https://www.youtube.com/feed/trending", "Tendencias - YouTube"),
        ("https://www.renfe.com/", "Billetes de tren - Renfe"),
        ("https://www.google.com/search?q=horario+farmacia", "horario farmacia - Busqueda"),
        ("https://www.idealista.com/alquiler-viviendas/", "Alquiler - Idealista"),
        ("https://www.elcorteingles.es/", "El Corte Ingles"),
        ("https://www.netflix.com/browse", "Inicio - Netflix"),
        ("https://www.glovoapp.com/", "Pedir - Glovo"),
        ("https://www.pccomponentes.com/portatiles", "Portatiles - PcComponentes"),
        ("https://www.google.com/maps/dir/", "Como llegar - Google Maps"),
        ("https://es.wikipedia.org/wiki/Selva_Negra", "Selva Negra - Wikipedia"),
    ],
    "tr": [
        ("https://www.hurriyet.com.tr/", "Hurriyet - Haberler"),
        ("https://www.mgm.gov.tr/", "Hava Durumu - MGM"),
        ("https://www.nefisyemektarifleri.com/", "Yemek Tarifleri"),
        ("https://www.fanatik.com.tr/futbol", "Futbol - Fanatik"),
        ("https://www.hepsiburada.com/cok-satanlar", "Cok Satanlar - Hepsiburada"),
        ("https://www.sahibinden.com/", "sahibinden.com"),
        ("https://www.youtube.com/feed/trending", "Trendler - YouTube"),
        ("https://www.tcddtasimacilik.gov.tr/", "Tren Bileti - TCDD"),
        ("https://www.google.com/search?q=eczane+nobetci", "nobetci eczane - Arama"),
        ("https://www.hepsiemlak.com/kiralik", "Kiralik - Hepsiemlak"),
        ("https://www.trendyol.com/", "Trendyol"),
        ("https://www.netflix.com/browse", "Ana Sayfa - Netflix"),
        ("https://www.yemeksepeti.com/", "Yemek Sepeti"),
        ("https://www.vatanbilgisayar.com/notebook/", "Notebook - Vatan"),
        ("https://www.google.com/maps/dir/", "Yol Tarifi - Google Maps"),
        ("https://tr.wikipedia.org/wiki/Kara_Orman", "Kara Orman - Vikipedi"),
    ],
}
# Tippfehler-Schutz: ungueltige Eintraege entfernen
WEB["de"] = [(u, t) for (u, t) in WEB["de"] if u.startswith("http") and " " not in u]

# ---------------------------------------------------------------------
# Dokumente  (name, kind, beschreibung)
# ---------------------------------------------------------------------
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
        ("Bewerbung_Anschreiben.docx", "docx", "Bewerbungsanschreiben"),
        ("Mietnebenkosten_2025.xlsx", "xlsx", "Nebenkostenabrechnung"),
        ("Reiseplan_Italien.docx", "docx", "Reiseplan"),
        ("Rechnung_Handwerker.pdf", "pdf", "Handwerkerrechnung"),
        ("Notizen_Meeting.txt", "txt", "Meeting-Notizen"),
        ("Geburtstagsliste.csv", "csv", "Geburtstagsliste"),
        ("Steuer_Belege_2025.xlsx", "xlsx", "Steuerbelege"),
        ("Wartung_Auto.pdf", "pdf", "Wartungsnachweis"),
        ("Lebenslauf.docx", "docx", "Lebenslauf"),
        ("Kochbuch_Favoriten.txt", "txt", "Lieblingsrezepte"),
    ],
    "en": [
        ("ShoppingList.txt", "txt", "Shopping list"),
        ("Recipe_Lasagne.pdf", "pdf", "Recipe"),
        ("Insurance_Policy.pdf", "pdf", "Insurance documents"),
        ("Vacation_Packing.txt", "txt", "Packing list"),
        ("Budget.csv", "csv", "Household budget"),
        ("Statement_Export.csv", "csv", "Bank statement"),
        ("CoverLetter.docx", "docx", "Cover letter"),
        ("Utilities_2025.xlsx", "xlsx", "Utility costs"),
        ("TripPlan_Italy.docx", "docx", "Trip plan"),
        ("Invoice_Plumber.pdf", "pdf", "Plumber invoice"),
        ("MeetingNotes.txt", "txt", "Meeting notes"),
        ("Birthdays.csv", "csv", "Birthday list"),
        ("Tax_Receipts_2025.xlsx", "xlsx", "Tax receipts"),
        ("Car_Service.pdf", "pdf", "Service record"),
        ("Resume.docx", "docx", "Resume"),
    ],
    "fr": [
        ("ListeCourses.txt", "txt", "Liste de courses"),
        ("Recette_Lasagne.pdf", "pdf", "Recette"),
        ("Assurance_Contrat.pdf", "pdf", "Documents d'assurance"),
        ("Budget_Menage.csv", "csv", "Budget menager"),
        ("LettreMotivation.docx", "docx", "Lettre de motivation"),
        ("Charges_2025.xlsx", "xlsx", "Charges"),
        ("Voyage_Italie.docx", "docx", "Plan de voyage"),
        ("Facture_Plombier.pdf", "pdf", "Facture plombier"),
        ("Notes_Reunion.txt", "txt", "Notes de reunion"),
        ("CV.docx", "docx", "Curriculum vitae"),
    ],
    "es": [
        ("ListaCompra.txt", "txt", "Lista de la compra"),
        ("Receta_Lasana.pdf", "pdf", "Receta"),
        ("Seguro_Poliza.pdf", "pdf", "Documentos de seguro"),
        ("Presupuesto.csv", "csv", "Presupuesto domestico"),
        ("CartaPresentacion.docx", "docx", "Carta de presentacion"),
        ("Gastos_2025.xlsx", "xlsx", "Gastos"),
        ("Viaje_Italia.docx", "docx", "Plan de viaje"),
        ("Factura_Fontanero.pdf", "pdf", "Factura fontanero"),
        ("Notas_Reunion.txt", "txt", "Notas de reunion"),
        ("CV.docx", "docx", "Curriculum"),
    ],
    "tr": [
        ("AlisverisListesi.txt", "txt", "Alisveris listesi"),
        ("Tarif_Lazanya.pdf", "pdf", "Yemek tarifi"),
        ("Sigorta_Police.pdf", "pdf", "Sigorta belgeleri"),
        ("AileButcesi.csv", "csv", "Ev butcesi"),
        ("OnYazi.docx", "docx", "Basvuru on yazisi"),
        ("Giderler_2025.xlsx", "xlsx", "Giderler"),
        ("Seyahat_Italya.docx", "docx", "Seyahat plani"),
        ("Fatura_Tesisatci.pdf", "pdf", "Tesisatci faturasi"),
        ("Toplanti_Notlari.txt", "txt", "Toplanti notlari"),
        ("Ozgecmis.docx", "docx", "Ozgecmis"),
    ],
}

# ---------------------------------------------------------------------
# SMS-Texte (Alltag)
# ---------------------------------------------------------------------
SMS = {
    "de": [
        "Bist du heute Abend zuhause?", "Kannst du Brot mitbringen?",
        "Termin beim Zahnarzt verschoben auf Donnerstag.", "Danke fuer gestern :)",
        "Bin 10 Min spaeter.", "Paket ist angekommen.", "Wie war dein Tag?",
        "Treffen wir uns um 18 Uhr?", "Hast du den Schluessel?", "Gute Besserung!",
        "Ich hol die Kinder ab.", "Tankst du bitte noch?", "Wo parkst du?",
        "Glueckwunsch zum Geburtstag!", "Schaffst du es zum Essen?",
        "Hab den Termin bestaetigt.", "Bringst du Milch mit?", "Bin unterwegs.",
        "Melde mich spaeter.", "Hast du gut geschlafen?", "Bis gleich!",
        "Kannst du anrufen?", "Alles klar bei dir?", "Wetter wird besser morgen.",
        "Vergiss den Muell nicht.",
    ],
    "en": [
        "Are you home tonight?", "Can you grab some bread?",
        "Dentist moved to Thursday.", "Thanks for yesterday :)",
        "Running 10 min late.", "Parcel arrived.", "How was your day?",
        "Meet at 6?", "Do you have the key?", "Get well soon!",
        "I'll pick up the kids.", "Can you fill up the car?", "Where did you park?",
        "Happy birthday!", "Can you make dinner?", "Confirmed the appointment.",
        "Bring milk please?", "On my way.", "Call you later.", "Sleep well?",
        "See you soon!", "Can you call?", "All good?", "Weather's better tomorrow.",
        "Don't forget the bins.",
    ],
    "fr": [
        "Tu es a la maison ce soir ?", "Tu peux prendre du pain ?",
        "Rendez-vous dentiste repousse a jeudi.", "Merci pour hier :)",
        "J'arrive avec 10 min de retard.", "Le colis est arrive.", "Ta journee ?",
        "On se voit a 18h ?", "Tu as la cle ?", "Bon retablissement !",
        "Je recupere les enfants.", "Tu peux faire le plein ?", "Tu t'es gare ou ?",
        "Joyeux anniversaire !", "Tu peux appeler ?", "Tout va bien ?",
    ],
    "es": [
        "Estas en casa esta noche?", "Puedes traer pan?",
        "Cita del dentista movida al jueves.", "Gracias por lo de ayer :)",
        "Llego 10 min tarde.", "El paquete ha llegado.", "Que tal tu dia?",
        "Quedamos a las 18?", "Tienes la llave?", "Que te mejores!",
        "Recojo a los ninos.", "Puedes echar gasolina?", "Donde aparcaste?",
        "Feliz cumpleanos!", "Puedes llamar?", "Todo bien?",
    ],
    "tr": [
        "Bu aksam evde misin?", "Ekmek alabilir misin?",
        "Disci randevusu persembeye alindi.", "Dun icin tesekkurler :)",
        "10 dakika gecikecegim.", "Kargo geldi.", "Gunun nasildi?",
        "Saat 18'de bulusalim mi?", "Anahtar sende mi?", "Gecmis olsun!",
        "Cocuklari ben alirim.", "Benzin alir misin?", "Nereye park ettin?",
        "Dogum gunun kutlu olsun!", "Arayabilir misin?", "Her sey yolunda mi?",
    ],
}

# ---------------------------------------------------------------------
# Kontaktnamen (Noise)
# ---------------------------------------------------------------------
CONTACTS = {
    "de": ["Mama", "Papa", "Lukas Berger", "Sandra Wolf", "Dr. Hoffmann",
           "Pizzeria Bella", "Werkstatt", "Apotheke", "Kita Sonnenschein",
           "Oma", "Nachbar Klaus", "Friseur", "Tierarzt", "Hausarzt",
           "Vermieter", "Versicherung", "Steuerberater", "Yoga Studio"],
    "en": ["Mum", "Dad", "Lucas Brown", "Sandra Wolf", "Dr. Carter",
           "Pizza Place", "Garage", "Pharmacy", "Daycare", "Grandma",
           "Neighbor Joe", "Hairdresser", "Vet", "GP", "Landlord",
           "Insurance", "Accountant", "Gym"],
    "fr": ["Maman", "Papa", "Lucas Bernard", "Sandra Petit", "Dr. Martin",
           "Pizzeria Bella", "Garage", "Pharmacie", "Creche", "Mamie",
           "Voisin Paul", "Coiffeur", "Veterinaire", "Medecin"],
    "es": ["Mama", "Papa", "Lucas Garcia", "Sandra Lopez", "Dr. Martinez",
           "Pizzeria Bella", "Taller", "Farmacia", "Guarderia", "Abuela",
           "Vecino Juan", "Peluquero", "Veterinario", "Medico"],
    "tr": ["Anne", "Baba", "Mehmet Yilmaz", "Ayse Demir", "Dr. Kaya",
           "Pizzaci", "Tamirci", "Eczane", "Kres", "Babaanne",
           "Komsu Ali", "Kuafor", "Veteriner", "Doktor"],
}

# ---------------------------------------------------------------------
# Noise-Apps (Bundle-IDs/Pakete) — sprachunabhaengig, je Plattform
# ---------------------------------------------------------------------
APPS = {
    "ios": ["com.spotify.client", "com.netflix.Netflix", "com.google.Maps",
            "com.amazon.Amazon", "com.pinterest", "com.zhiliaoapp.musically",
            "com.linkedin.LinkedIn", "com.toyopagroup.picaboo", "com.king.candycrushsaga",
            "com.google.Gmail", "com.apple.mobilenotes", "com.duolingo.DuolingoMobile",
            "com.ubercab.UberClient", "com.booking.Booking", "com.spotify.podcasts",
            "com.reddit.Reddit", "com.tinyspeck.chatlyio", "ph.telegra.Telegraph",
            "com.burbn.instagram", "com.facebook.Messenger"],
    "android": ["com.spotify.music", "com.netflix.mediaclient", "com.google.android.apps.maps",
                "com.amazon.mShop.android.shopping", "com.pinterest", "com.zhiliaoapp.musically",
                "com.linkedin.android", "com.instagram.android", "com.king.candycrushsaga",
                "com.google.android.gm", "com.dropbox.android", "com.duolingo",
                "com.ubercab", "com.booking", "com.google.android.youtube",
                "com.reddit.frontpage", "org.telegram.messenger", "com.facebook.orca",
                "com.snapchat.android", "com.microsoft.office.outlook"],
}


def _g(d, lang):
    return d.get(lang, d["de"])


def web(lang):
    return _g(WEB, lang)


def docs(lang):
    return _g(DOCS, lang)


def sms(lang):
    return _g(SMS, lang)


def contacts(lang):
    return _g(CONTACTS, lang)


def apps(platform):
    return APPS.get(platform, [])


if __name__ == "__main__":
    for L in ("de", "en", "fr", "es", "tr"):
        print(f"{L}: web={len(web(L))} docs={len(docs(L))} sms={len(sms(L))} contacts={len(contacts(L))}")
    print("apps ios/android:", len(apps("ios")), len(apps("android")))
