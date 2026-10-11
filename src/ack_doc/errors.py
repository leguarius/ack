"""Catalogue centralisé des codes d'erreur et codes retour (TEC-049, TEC-051)."""

EXIT_SUCCESS = 0
EXIT_VALIDATION = 1
EXIT_TECHNICAL = 2

# Non-conformités documentaires (code retour 1)
MISSING_TAG = "MISSING_TAG"
DUPLICATE_TAG = "DUPLICATE_TAG"
UNCLOSED_TAG = "UNCLOSED_TAG"
UNMATCHED_CLOSING_TAG = "UNMATCHED_CLOSING_TAG"
MALFORMED_TAG = "MALFORMED_TAG"
NESTED_TAG = "NESTED_TAG"
INVALID_ANACK = "INVALID_ANACK"
INVALID_ORNUM = "INVALID_ORNUM"
INVALID_EXSUM = "INVALID_EXSUM"
DUPLICATE_ANACK_ORNUM = "DUPLICATE_ANACK_ORNUM"
ANACK_NOT_IN_TEMPLATE = "ANACK_NOT_IN_TEMPLATE"
PDF_UNREADABLE = "PDF_UNREADABLE"
PDF_NO_TEXT = "PDF_NO_TEXT"
INVALID_TEMPLATE = "INVALID_TEMPLATE"
DUPLICATE_TEMPLATE_ANACK = "DUPLICATE_TEMPLATE_ANACK"
NO_PDF_FOUND = "NO_PDF_FOUND"
EXSUM_CROSSES_PAGE = "EXSUM_CROSSES_PAGE"

# Erreurs techniques ou d'exécution (code retour 2)
OUTPUT_EXISTS = "OUTPUT_EXISTS"
INPUT_DIR_ERROR = "INPUT_DIR_ERROR"
TEMPLATE_READ_ERROR = "TEMPLATE_READ_ERROR"
TEMPLATE_ENCODING_ERROR = "TEMPLATE_ENCODING_ERROR"
OUTPUT_DIR_ERROR = "OUTPUT_DIR_ERROR"
JOURNAL_DIR_ERROR = "JOURNAL_DIR_ERROR"
PATH_COLLISION = "PATH_COLLISION"
IO_ERROR = "IO_ERROR"
RENDER_ERROR = "RENDER_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

CATALOG: dict[str, str] = {
    MISSING_TAG: "Balise obligatoire absente",
    DUPLICATE_TAG: "Balise présente plusieurs fois",
    UNCLOSED_TAG: "Balise ouverte non fermée",
    UNMATCHED_CLOSING_TAG: "Fermeture sans ouverture",
    MALFORMED_TAG: "Syntaxe incorrecte",
    NESTED_TAG: "Balises imbriquées",
    INVALID_ANACK: "Clé analytique invalide",
    INVALID_ORNUM: "Numéro d'ordre invalide",
    INVALID_EXSUM: "Résumé invalide",
    DUPLICATE_ANACK_ORNUM: "Couple clé/ordre dupliqué",
    ANACK_NOT_IN_TEMPLATE: "Clé absente du modèle",
    PDF_UNREADABLE: "PDF impossible à lire",
    PDF_NO_TEXT: "PDF sans texte exploitable",
    OUTPUT_EXISTS: "Fichier de sortie existant",
    INVALID_TEMPLATE: "Template vide ou structure non conforme",
    DUPLICATE_TEMPLATE_ANACK: "Clé ANACK répétée dans le template",
    NO_PDF_FOUND: "Aucun PDF découvert dans le répertoire d'entrée",
    EXSUM_CROSSES_PAGE: "Résumé EXSUM réparti sur plusieurs pages",
    INPUT_DIR_ERROR: "Répertoire d'entrée inexistant ou inaccessible",
    TEMPLATE_READ_ERROR: "Template inexistant ou illisible",
    TEMPLATE_ENCODING_ERROR: "Template non encodé en UTF-8 valide",
    OUTPUT_DIR_ERROR: "Répertoire de sortie inexistant ou inaccessible",
    JOURNAL_DIR_ERROR: "Répertoire du journal inexistant ou inaccessible",
    PATH_COLLISION: "Collision destructrice entre chemins de fichiers",
    IO_ERROR: "Erreur d'accès ou d'écriture de fichier",
    RENDER_ERROR: "Échec de la génération du PDF",
    INTERNAL_ERROR: "Erreur interne",
}


class TechnicalError(Exception):
    """Erreur technique ou d'exécution : code retour 2."""

    def __init__(self, code: str, message: str, file: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.file = file
