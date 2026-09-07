class MbrolaRenderer:

    def render(self, pho_file, wav_file):
        subprocess.run(
            [
                "mbrola",
                self.voice,
                pho_file,
                wav_file,
            ],
            check=True,
        )