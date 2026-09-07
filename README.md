# Singender Aufzug (Singing Elevator)

An interactive, AI-powered singing elevator installation for the [Ligeti Zentrum](https://ligetizentrum.de) in Hamburg-Harburg. The elevator persona — named **Elfi** — converses with guests in German during the ~30-second ride from the ground floor to the Production Lab on the 10th floor. Every response is sung, not spoken.

## Quickstart Demo
cd ~/singender-aufzug
source .venv/bin/activate
python main.py

## Overview

```
Microphone → Whisper (STT) → Qwen LLM (llama-server) → TechScore → MBROLA → Speakers
```

The entire pipeline runs **locally** on a Raspberry Pi. No cloud services, no internet required.

### Persona: Elfi

Elfi is the friendly, warm, and slightly playful singing elevator. Full character description in [`docs/persona.md`](docs/persona.md) (German). Key traits:

- Non-binary, addressed by name ("Elfi") — pronouns are avoided
- Answers questions about the venue, the event, and the program
- Responses are short (≤2 sentences), singable, and in German
- No jokes, no long stories, no unsolicited questions

## Project Structure

```
singender-aufzug/
├── main.py                  # Main interactive loop (endless record→sing→play)
├── voice_demo_stable.py     # Single-shot demo with retry on bad recording
├── voice_demo.py            # Shared helpers (used by voice_demo_stable.py)
├── config.py                # Hardware config: MBROLA voice path, audio device
├── elevator.py              # Hand-crafted phoneme/note score for "hereinspaziert"
│
├── audio/                   # Audio rendering pipeline
│   ├── pho.py               # Phoneme data structures
│   ├── pho_writer.py        # Write MBROLA .pho files
│   ├── mbrola.py            # MBROLA binary wrapper
│   └── renderer.py          # High-level MBROLA renderer
│
├── language/                # German text → phonemes → syllables
│   ├── analyzer.py          # Text analysis (syllables, stress)
│   ├── phonemizer.py        # Grapheme-to-phoneme conversion
│   ├── phoneme_normalizer.py # MBROLA-specific phoneme normalization (de4 voice)
│   └── aligner.py           # Align phoneme groups to syllable counts
│
├── music/                   # Score composition (text → notes & timing)
│   ├── tech_score.py        # TechScore data structures (notes, phrases, cadences)
│   ├── tech_composer.py     # Compose TechScore from words & syllables
│   ├── tech_duration.py     # Realize symbolic durations to milliseconds
│   ├── melody.py            # Melody generation
│   ├── prosody.py           # Prosody & pitch targets
│   ├── performance.py       # Performance planner (gestures, F0 targets)
│   └── events.py            # Musical event definitions
│
├── singing/                 # Singing synthesis
│   ├── tech_singer.py       # TechScore → phoneme list renderer
│   └── singer.py            # Generic singer interface
│
├── speech/                  # Speech recognition
│   ├── recorder.py          # Simple arecord-based audio recorder
│   ├── recorder_vad.py      # Recorder with voice activity detection
│   └── whisper_stt.py       # whisper.cpp CLI wrapper
│
├── llm/                     # Language model integration
│   ├── local_response_generator.py  # llama-server client (Qwen 1.7B)
│   ├── prompt_loader.py     # Load system prompts from config/
│   ├── prompt_router.py     # Route to dialogue templates
│   └── german_terms.py      # German-specific LLM guidance
│
├── config/                  # LLM prompts & event data
│   ├── system_prompt.txt    # System prompt for Elfi's persona
│   ├── conversation_rules.txt
│   ├── event.txt            # Current event details
│   ├── program.txt          # Event program
│   └── ligeti_zentrum.txt   # Venue information
│
├── dialogues/               # Dialogue templates by topic
│   ├── greetings.txt
│   ├── orientation.txt
│   ├── event_questions.txt
│   ├── artist.txt
│   ├── smalltalk.txt
│   └── fallback.txt
│
├── debug/                   # Diagnostics
│   └── phoneme_diagnostics.py
│
├── docs/
│   └── persona.md           # Elfi character description (German)
│
└── models/llm/
    └── Qwen3-1.7B-Q4_K_M.gguf   # German-capable small LLM
```

## Hardware Requirements

- **Raspberry Pi** (tested on Pi 4/5, Raspberry Pi OS)
- **USB microphone** (or any ALSA capture device at `plughw:0,0`)
- **Speakers / amplifier** (ALSA playback)
- **~3-4 GB free RAM** for the LLM (Qwen3-1.7B Q4_K_M)

## Software Dependencies

### System-level (must be installed separately)

| Component | Path / Package | Purpose |
|-----------|---------------|---------|
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | `~/whisper.cpp/build/bin/whisper-cli` | Speech-to-text (German) |
| Whisper model | `~/whisper.cpp/models/ggml-tiny.bin` | STT model (tiny is sufficient) |
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | `~/llama.cpp/build/bin/llama-server` | LLM inference server |
| Qwen model | `models/llm/Qwen3-1.7B-Q4_K_M.gguf` | German-capable small LLM |
| [MBROLA](https://github.com/numediart/MBROLA) | system PATH (`mbrola`) | Diphone speech synthesis |
| MBROLA de4 voice | `/usr/share/mbrola/de4/de4` | German female diphone database |
| `arecord` / `aplay` | ALSA utils | Audio capture & playback |

### Python

**Python 3.12+** (developed on 3.13). The project uses only the standard library — **no pip packages required**. All external tools (whisper, llama, mbrola) are called as subprocesses.

### Install system dependencies (Raspberry Pi / Debian)

```bash
# ALSA audio tools
sudo apt install alsa-utils

# MBROLA and German voice
sudo apt install mbrola mbrola-de4

# Build whisper.cpp
cd ~
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
bash ./models/download-ggml-model.sh tiny

# Build llama.cpp
cd ~
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# Download Qwen model (1.7B Q4_K_M quantized)
# Place it at: models/llm/Qwen3-1.7B-Q4_K_M.gguf
# Recommended source: Hugging Face → Qwen/Qwen3-1.7B-GGUF
```

## Running the Demos

### 1. Interactive Loop (endless mode)

```bash
python main.py
```

Press **Enter** to record 12 seconds of audio. The full pipeline runs:

1. Records from microphone
2. Transcribes with Whisper
3. Generates Elfi's response via local LLM
4. Composes a TechScore (notes, rhythm, prosody)
5. Renders with MBROLA → WAV file
6. Plays through speakers
7. Waits for next Enter press

Press **Ctrl+C** to exit.

### 2. Single-shot Demo (with retry)

```bash
python voice_demo_stable.py
```

Same pipeline but runs once. If the recording is bad or Whisper returns nothing, you get one automatic retry. The user can also manually reject (`r`) and re-record.

### 3. Text-direct Mode (no microphone, no LLM)

```bash
python main.py "Guten Abend und herzlich willkommen"
```

Skips the recording and LLM. Renders the given German text directly to song. Useful for testing the singing pipeline.

```bash
python main.py --bpm 120 --diagnostics "Hallo, schön dass du da bist"
```

- `--bpm N`: set tempo (default: 96)
- `--diagnostics`: print detailed phoneme timing, note durations, and pitch targets

### 4. Play a Pre-rendered Phrase

```bash
aplay singender_aufzug.wav
```

After any run, the file `singender_aufzug.wav` contains the last rendered song. The corresponding `.pho` file is archived into `pho_archiv.zip` before each overwrite.

## Configuration

### `config.py`

```python
MBROLA_VOICE_PATH = Path("/usr/share/mbrola/de4/de4")
AUDIO_DEVICE = "plughw:0,0"
```

- Change `MBROLA_VOICE_PATH` if using a different MBROLA voice
- Change `AUDIO_DEVICE` to match your ALSA capture device (`arecord -L` to list)

### LLM Config

Edit files in `config/` to customize:

| File | Purpose |
|------|---------|
| `system_prompt.txt` | Elfi's persona, behavior rules, tone |
| `event.txt` | Current event name, date, price, program |
| `program.txt` | Detailed event program |
| `ligeti_zentrum.txt` | Venue facts and information |
| `conversation_rules.txt` | Response constraints |

The main prompt template is hardcoded in `llm/local_response_generator.py` method `_build_compact_prompt()`. This is where you update the event date, program details, and example Q&A pairs.

### Audio Recording

- `main.py` uses `speech/recorder_vad.py` — records 12 seconds
- `voice_demo_stable.py` uses `speech/recorder_vad.py` — same
- Both record mono 16kHz 16-bit WAV via `arecord`

### MBROLA Voice

The project uses the German **de4** voice (female). Phoneme normalization in `language/phoneme_normalizer.py` is tuned specifically for de4. If you switch voices, adjust the normalization rules.

## How the Singing Works

The pipeline that turns German text into sung audio:

1. **Text Analysis** (`language/`): Tokenize → syllable segmentation → stress assignment
2. **Phonemization** (`language/phonemizer.py`): Graphemes → phonemes, grouped by syllable
3. **Phoneme Normalization** (`language/phoneme_normalizer.py`): Adjust phonemes for the de4 MBROLA voice (e.g., glottal stops, vowel length)
4. **Alignment** (`language/aligner.py`): Match phoneme groups to syllables
5. **Score Composition** (`music/tech_composer.py`): Assign MIDI notes, note types, durations, and phrase structure (cadences, pauses) — produces a `TechScore`
6. **Duration Realization** (`music/tech_duration.py`): Convert symbolic beats to millisecond timings
7. **Performance Planning** (`music/performance.py`): Add gestures (attack/hold/release) and pitch targets (microtonal F0 curves)
8. **Singing Synthesis** (`singing/tech_singer.py`): Flatten the performance into a list of timed phonemes
9. **PHO Output** (`audio/pho_writer.py`): Write the MBROLA `.pho` file format
10. **Audio Rendering** (`audio/renderer.py`): Call `mbrola` binary to produce the final `.wav`

The previous run's `.pho` is archived into `pho_archiv.zip` before being overwritten.

## Key Classes & Flow

### `main.py` (interactive loop)

```
main()
 ├─ check_system()         # Verify all binaries and models exist
 ├─ LocalResponseGenerator  # Start llama-server, check health
 └─ while True:
      ├─ record_audio()     # 12s from microphone
      ├─ transcribe()       # whisper-cli
      ├─ generator.generate()  # LLM response
      ├─ render_text()      # Text → song pipeline
      │   ├─ TextAnalyzer / SyllablePhonemizer / SyllableAligner
      │   ├─ TechScoreComposer.compose()
      │   ├─ TechDurationPlanner.realize()
      │   ├─ PerformancePlanner.plan()
      │   └─ TechScoreSinger.sing()
      └─ play_audio()       # aplay
```

### `LocalResponseGenerator` (llm/local_response_generator.py)

- Manages the `llama-server` subprocess lifecycle (`start_server` / `stop_server`)
- Health-checks the server via `/health` endpoint
- Sends completion requests to `http://127.0.0.1:8080/completion`
- Built-in fallback responses for common question patterns
- Echo detection to prevent the LLM from repeating the input
- Response cleaning (strip model artifacts, limit to 2 sentences, 30 words max)

### `TechScoreComposer` (music/tech_composer.py)

Takes `WordMaterial` (word + syllable-phoneme groups) and composes a musical score:

- Assigns pitches based on syllable stress (stressed → higher or more stable notes)
- Creates rhythmic patterns (note types: whole, half, quarter, etc.)
- Adds phrase-level structure (cadences, pauses between phrases)
- Respects punctuation (`.` = falling cadence, `?` = rising, `!` = emphatic)

## Troubleshooting

### "Datei fehlt: …" (system check fails)

Ensure all paths in `check_system()` (in `main.py` or `voice_demo_stable.py`) point to existing files. The expected locations are:

- `~/whisper.cpp/build/bin/whisper-cli`
- `~/whisper.cpp/models/ggml-tiny.bin`
- `~/llama.cpp/build/bin/llama-server`
- `models/llm/Qwen3-1.7B-Q4_K_M.gguf` (relative to project root)

### LLM returns garbage or empty

1. Check if `llama-server` is running: `curl http://127.0.0.1:8080/health`
2. Verify the model file exists and is the correct format (Q4_K_M GGUF)
3. Increase `n_predict` in `generate()` if answers are cut off
4. Check system prompt in `_build_compact_prompt()` — event date might be outdated

### Whisper doesn't understand speech

- The tiny model only handles clear, close-mic German speech well
- Ensure the microphone is at `plughw:0,0` (`arecord -l` to list devices)
- Adjust `RECORDING_SECONDS` (default: 12) if needed
- For better accuracy, download a larger Whisper model

### MBROLA errors

- Verify `mbrola` is in PATH: `which mbrola`
- Verify the de4 voice database exists: `ls /usr/share/mbrola/de4/de4`
- Some phoneme sequences may not exist in the de4 database — the normalizer handles most cases, but edge cases with unusual German words may fail

### Audio device issues

```bash
# List capture devices
arecord -l

# List playback devices
aplay -l

# Test microphone
arecord -d 3 -f cd -t wav test.wav

# Test speaker
aplay test.wav
```

Update `AUDIO_DEVICE` in `config.py` if needed.

## Development Notes

### Code Style

- Python 3.12+ with full type hints (`from __future__ import annotations`)
- Google-style docstrings on public methods
- Standard library only — no external Python dependencies
- German comments and variable names throughout (domain language)

### Adding a New Dialogue Topic

1. Add a `.txt` template in `dialogues/`
2. Add routing logic in `llm/prompt_router.py`
3. Update the prompt in `llm/local_response_generator.py` `_build_compact_prompt()` if needed

### Changing the LLM Model

1. Place the new GGUF file in `models/llm/`
2. Update `MODEL_PATH` in `llm/local_response_generator.py`
3. Adjust `n_predict`, `temperature`, and stop tokens in `generate()` as needed
4. Test that the model understands German and follows the system prompt

### Adding a New MBROLA Voice

1. Install the voice database (e.g., `mbrola-de6` for another German voice)
2. Update `MBROLA_VOICE_PATH` in `config.py`
3. Adjust phoneme normalization in `language/phoneme_normalizer.py` — each MBROLA voice has different phoneme inventories

## Backup

A timestamped backup was created at:

```
~/singender-aufzug_backup_20260730_0932.tar.gz
```

It excludes `.venv`, `__pycache__`, and the `models/` directory.

## License

Internal project for the Ligeti Zentrum Hamburg. Not for redistribution.
