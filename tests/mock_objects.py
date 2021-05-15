class MockSynth(object):
    def __init__(self):
        self.audio_driver = None

    def sfunload(self, sfid):
        return True

    def program_reset(self):
        return True

    def get_samples(self, len):
        return True


class MockWav(object):
    def writeframes(self, data):
        return True

    def close(self):
        return True


class MockFluidSynthSequencer(object):
    def __init__(self):
        self.fs = MockSynth()
        self.sfid = None
        self.wav = MockWav()

    def load_sound_font(self, path):
        return True

    def start_audio_output(self, driver):
        return True

    def set_instrument(self, channel, instr, bank):
        return True

    def start_recording(self, file):
        return True

    def play_Note(self, note):
        return True

    def play_NoteContainer(self, nc):
        return True

    def play_Bar(self, bar):
        return True

    def play_Track(self, track):
        return True
