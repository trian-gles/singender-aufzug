#!/usr/bin/env python3
"""Interaktiver Texttest für Elfis Kontext und lokales LLM.

Beispiele:
    python3 tools/test_elfi_text.py --router-only
    python3 tools/test_elfi_text.py --model /Pfad/Qwen3-4B-Q4_K_M.gguf --start-server
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.local_response_generator import LocalResponseGenerator
from llm.prompt_router import PromptRouter


DEFAULT_MODEL = PROJECT_ROOT / "models" / "llm" / "Qwen3-4B-Q4_K_M.gguf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Testet Elfis Antworten ohne Mikrofon, Audio und Raspberry Pi."
    )
    parser.add_argument(
        "--router-only",
        action="store_true",
        help="Nur sichere lokale Kontextantworten testen; kein LLM nötig.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help="Pfad zur Qwen-GGUF-Datei.",
    )
    parser.add_argument(
        "--llama-server",
        type=Path,
        default=Path(shutil.which("llama-server") or "llama-server"),
        help="Pfad zu llama-server.",
    )
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Startet llama-server automatisch und beendet ihn beim Verlassen.",
    )
    parser.add_argument(
        "--question",
        help="Stellt eine einzelne Frage statt des interaktiven Modus.",
    )
    return parser.parse_args()


def print_result(question: str, router: PromptRouter, generator: LocalResponseGenerator | None) -> None:
    if generator is None:
        answer = router.direct_response(question)
        if answer:
            print(f"Elfi [lokal] > {answer}")
        else:
            print("Elfi [LLM nötig] > Keine direkte Kontextantwort gefunden.")
        return

    result = generator.generate(question)
    print(f"Elfi [{result.source}] > {result.text}")


def main() -> None:
    args = parse_args()
    router = PromptRouter()
    generator: LocalResponseGenerator | None = None

    if not args.router_only:
        model = args.model.expanduser().resolve()
        llama_server = args.llama_server.expanduser()
        if not model.is_file():
            raise SystemExit(
                "Qwen-Modell nicht gefunden. Starte zunächst mit --router-only oder "
                "übergib den Pfad mit --model /Pfad/zur/Qwen3-4B-Q4_K_M.gguf."
            )
        if not llama_server.is_file():
            raise SystemExit(f"llama-server nicht gefunden: {llama_server}")
        generator = LocalResponseGenerator(
            llama_server=llama_server,
            model_path=model,
        )
        if args.start_server:
            generator.start_server()

    try:
        if args.question:
            print_result(args.question, router, generator)
            return

        mode = "nur Kontext" if generator is None else "Kontext und 4B-LLM"
        print(f"Elfi-Texttest ({mode}). Mit Enter oder /quit beenden.")
        while True:
            try:
                question = input("Du > ").strip()
            except EOFError:
                break
            if not question or question.casefold() in {"/quit", "/exit", "quit", "exit"}:
                break
            print_result(question, router, generator)
    finally:
        if generator is not None and args.start_server:
            generator.stop_server()


if __name__ == "__main__":
    main()
