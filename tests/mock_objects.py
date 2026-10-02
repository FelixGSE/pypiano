class MockSynth:
    def __init__(self) -> None:
        self.audio_driver = None

    def sfunload(self, sfid) -> bool:
        return True

    def program_reset(self) -> bool:
        return True

    def get_samples(self, len) -> bool:
        return True


class MockWav:
    def writeframes(self, data) -> bool:
        return True

    def close(self) -> bool:
        return True


class MockFluidSynthSequencer:
    def __init__(self) -> None:
        self.fs = MockSynth()
        self.sfid = None
        self.wav = MockWav()

    def load_sound_font(self, path) -> bool:
        return True

    def start_audio_output(self, driver) -> bool:
        return True

    def set_instrument(self, channel, instr, bank) -> bool:
        return True

    def start_recording(self, file) -> bool:
        return True

    def play_Note(self, note) -> bool:
        return True

    def play_NoteContainer(self, nc) -> bool:
        return True

    def play_Bar(self, bar) -> bool:
        return True

    def play_Track(self, track) -> bool:
        return True
