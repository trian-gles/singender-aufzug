import subprocess
from pathlib import Path

OUTPUT_FILE = Path("answer.wav")
AUDIO_DEVICE = "plughw:2,0"


def speak(text: str) -> None:
    if not text.strip():
        raise ValueError("Der Text darf nicht leer sein.")

    subprocess.run(
        [
            "espeak-ng",
            "-v",
            "de",
            "-s",
            "145",
            "-p",
            "45",
            "-w",
            str(OUTPUT_FILE),
            text,
        ],
        check=True,
    )

    subprocess.run(
        [
            "aplay",
            "-D",
            AUDIO_DEVICE,
            str(OUTPUT_FILE),
        ],
        check=True,
    )


def main() -> None:
    print("Singender Aufzug – Textmodus")
    print("Beenden mit: ende")

    while True:
        text = input("\nDu: ").strip()

        if text.lower() in {"ende", "exit", "quit"}:
            print("Aufzug beendet.")
            break

        try:
            speak(text)
        except (ValueError, subprocess.CalledProcessError) as error:
            print(f"Fehler: {error}")


if __name__ == "__main__":
    main()
