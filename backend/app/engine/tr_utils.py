TR_UPPER_MAP = str.maketrans({
    "i": "İ",
    "ı": "I",
    "ğ": "Ğ",
    "ü": "Ü",
    "ş": "Ş",
    "ö": "Ö",
    "ç": "Ç",
})

def tr_upper(text: str) -> str:
    return text.translate(TR_UPPER_MAP).upper()
