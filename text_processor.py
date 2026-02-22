import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normaliza encoding Unicode (NFC) y limpia espacios extra."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize_sentences(text: str) -> list[str]:
    """Divide el texto en oraciones por puntuación fuerte."""
    text = normalize_text(text)
    sentences = re.split(r"[.!?;:]+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 3]


def tokenize_words(sentence: str) -> list[str]:
    """Extrae sólo tokens alfabéticos en minúsculas (incluye tildes y ñ)."""
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+", sentence.lower())


def quantify_word(word: str) -> float:
    """
    Calcula el valor WPA de una palabra.
    Cada carácter se pondera por su posición (1-indexed) y se promedia por longitud.
    """
    if not word:
        return 0.0
    return sum(ord(c) * (i + 1) for i, c in enumerate(word)) / len(word)


def normalize_values(values: list[float]) -> list[int]:
    """
    Aplica la función de transferencia del proyecto al intervalo [0, 127]:
        f(x) = ((x - x_min) / (x_max - x_min)) * 127
    Si todos los valores son iguales, se retorna el valor central (64).
    """
    if not values:
        return []
    x_min, x_max = min(values), max(values)
    if x_max == x_min:
        return [64] * len(values)
    return [int(((x - x_min) / (x_max - x_min)) * 127) for x in values]


def process_sentence(sentence: str) -> list[tuple[str, float, int]]:
    """
    Procesa una oración y devuelve lista de tuplas (palabra, valor_raw, valor_midi).
    La normalización se aplica dentro de cada oración (contexto local).
    """
    words = tokenize_words(sentence)
    if not words:
        return []
    raw_values = [quantify_word(w) for w in words]
    midi_values = normalize_values(raw_values)
    return list(zip(words, raw_values, midi_values))
