from __future__ import annotations

from dataclasses import replace
import unicodedata

from audio.pho import Phoneme


class GermanMbrolaNormalizer:
    """Kleine, explizite Anpassungsschicht zwischen eSpeak und MBROLA.

    Sie korrigiert keine allgemeine Aussprache, sondern nur bekannte
    Schnittstellenprobleme. Alle Regeln bleiben hier sichtbar und testbar.
    """

    SYMBOL_MAP = {
        # mb-de2/eSpeak nutzt für kurzes ü meist Y; nicht blind in y: umwandeln.
        "y": "Y",
    }

    WORD_OVERRIDES = {
        # Manche Installationen liefern für Grünzeug einen stimmlosen Anlaut.
        # Nur wortgebunden korrigieren, niemals global k -> g.
        "grunzeug": {0: "g"},
        "gruenzeug": {0: "g"},
    }

    def normalize_word(self, word: str, groups: list[list[Phoneme]]) -> list[list[Phoneme]]:
        normalized_word = self._normalize_text(word)
        flat_index = 0
        result: list[list[Phoneme]] = []
        overrides = self.WORD_OVERRIDES.get(normalized_word, {})
        for group in groups:
            new_group: list[Phoneme] = []
            for phoneme in group:
                symbol = self.SYMBOL_MAP.get(phoneme.symbol, phoneme.symbol)
                symbol = overrides.get(flat_index, symbol)
                new_group.append(replace(phoneme, symbol=symbol))
                flat_index += 1
            result.append(new_group)
        return result

    @staticmethod
    def _normalize_text(text: str) -> str:
        value = unicodedata.normalize("NFKD", text.lower())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return value.replace("ß", "ss")
