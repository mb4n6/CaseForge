#!/usr/bin/env python3
# =====================================================================
# i18n.py  —  Sprachschicht fuer CaseForge
# ---------------------------------------------------------------------
# Die ARTEFAKT-Inhalte stammen aus dem Spec (vom LLM in der gewaehlten
# Sprache verfasst) und werden von den Generatoren wortgetreu projiziert.
# Diese Schicht steuert daher (a) die Ausgabesprache des LLM-Vorschlags,
# (b) Framework-Texte (Katalog, Konsole) und (c) die Locale-Metadaten.
#
# Sprachcode-Konvention: BCP-47 (de-DE, en-US, fr-FR, es-ES, tr-TR).
# `short(locale)` -> ISO-639-1 ("de", "en", ...).
# =====================================================================

# Unterstuetzte Sprachen (Default zuerst). Erweiterbar.
SUPPORTED = {
    "de": {"locale": "de-DE", "name_de": "Deutsch",     "name_en": "German",
           "endonym": "Deutsch"},
    "en": {"locale": "en-US", "name_de": "Englisch",    "name_en": "English",
           "endonym": "English"},
    "fr": {"locale": "fr-FR", "name_de": "Franzoesisch", "name_en": "French",
           "endonym": "Français"},
    "es": {"locale": "es-ES", "name_de": "Spanisch",    "name_en": "Spanish",
           "endonym": "Español"},
    "tr": {"locale": "tr-TR", "name_de": "Tuerkisch",   "name_en": "Turkish",
           "endonym": "Türkçe"},
}
DEFAULT = "de"


def short(locale_or_code):
    """'de-DE' | 'Deutsch' | 'de' -> 'de' (ISO-639-1). Fallback: DEFAULT."""
    if not locale_or_code:
        return DEFAULT
    s = str(locale_or_code).strip().lower()
    if s[:2] in SUPPORTED:
        return s[:2]
    for code, meta in SUPPORTED.items():
        if s in (meta["locale"].lower(), meta["endonym"].lower(),
                 meta["name_en"].lower(), meta["name_de"].lower()):
            return code
    return DEFAULT


def locale(code):
    return SUPPORTED.get(short(code), SUPPORTED[DEFAULT])["locale"]


def endonym(code):
    return SUPPORTED.get(short(code), SUPPORTED[DEFAULT])["endonym"]


# ---- Framework-Strings (Konsole/Katalog) ----
STR = {
    "catalog_title":   {"de": "Artefakt-Katalog", "en": "Artifact Catalogue",
                        "fr": "Catalogue d'artefacts", "es": "Catálogo de artefactos",
                        "tr": "Artefakt Kataloğu"},
    "col_platform":    {"de": "Plattform", "en": "Platform", "fr": "Plateforme",
                        "es": "Plataforma", "tr": "Platform"},
    "col_artifact":    {"de": "Artefaktklasse", "en": "Artifact class", "fr": "Classe d'artefact",
                        "es": "Clase de artefacto", "tr": "Artefakt sınıfı"},
    "col_format":      {"de": "Format", "en": "Format", "fr": "Format", "es": "Formato", "tr": "Biçim"},
    "col_tool":        {"de": "Forensik-Tool", "en": "Forensic tool", "fr": "Outil forensique",
                        "es": "Herramienta forense", "tr": "Adli analiz aracı"},
    "source_master":   {"de": "Master", "en": "master", "fr": "master", "es": "master", "tr": "master"},
    "source_fallback": {"de": "Referenz-Fallback", "en": "reference fallback",
                        "fr": "repli de référence", "es": "respaldo de referencia",
                        "tr": "referans yedeği"},
}


def t(key, code):
    """Framework-String in der gewuenschten Sprache (Fallback: en, dann de)."""
    c = short(code)
    entry = STR.get(key, {})
    return entry.get(c) or entry.get("en") or entry.get("de") or key


def proposal_language_instruction(code):
    """Harte Anweisung an das LLM, den Fall in der gewaehlten Sprache zu verfassen."""
    name = SUPPORTED.get(short(code), SUPPORTED[DEFAULT])
    return (
        f"## AUSGABESPRACHE / OUTPUT LANGUAGE\n"
        f"Verfasse ALLE narrativen und inhaltlichen Felder des Case-Spec "
        f"(Personennamen-Stil, Nachrichtentexte, Dokumenttitel/-inhalte, "
        f"Browser-Titel, Lernziel-Beschreibung) AUSSCHLIESSLICH auf "
        f"**{name['endonym']}** ({name['locale']}). Technische Schluessel, "
        f"Bundle-IDs, Pfade, Feldnamen und das JSON-Schema bleiben unveraendert. "
        f"Setze meta.language_primary = \"{name['locale']}\".\n"
        f"Write ALL narrative/content fields of the case spec exclusively in "
        f"**{name['endonym']}** ({name['locale']}); keep technical keys, bundle IDs, "
        f"paths and the JSON schema unchanged."
    )


if __name__ == "__main__":
    for c in SUPPORTED:
        print(c, locale(c), endonym(c), "|", t("catalog_title", c))
    print("short('de-DE')=", short("de-DE"), "short('English')=", short("English"))
