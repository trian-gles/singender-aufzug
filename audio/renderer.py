from pathlib import Path
import subprocess


class MbrolaRenderer:
    def __init__(self, voice_path: str | Path) -> None:
        self.voice_path = Path(voice_path)

    def render(
        self,
        pho_path: str | Path,
        wav_path: str | Path,
    ) -> None:
        pho_path = Path(pho_path)
        wav_path = Path(wav_path)

        if not self.voice_path.exists():
            raise FileNotFoundError(
                f"MBROLA-Stimme nicht gefunden: {self.voice_path}"
            )

        if not pho_path.exists():
            raise FileNotFoundError(
                f"PHO-Datei nicht gefunden: {pho_path}"
            )

        subprocess.run(
            [
                "mbrola",
                str(self.voice_path),
                str(pho_path),
                str(wav_path),
            ],
            check=True,
        )