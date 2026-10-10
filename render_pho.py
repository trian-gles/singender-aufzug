from config import MBROLA_VOICE_PATH
from audio.renderer import MbrolaRenderer


MbrolaRenderer(MBROLA_VOICE_PATH).render(pho_path="./singender_aufzug.pho", wav_path="./melody.wav")
