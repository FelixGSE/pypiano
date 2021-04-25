from mingus.midi import pyfluidsynth as fs
import functools

def record(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        object_reference = args[0]
        recording_file = kwargs.get('recording_file', None)
        seconds = kwargs.get("seconds", 4)
        stop_recording = kwargs.get("stop_recording", True)

        if recording_file is not None:

            object_reference._stop_audio_output()

            object_reference.start_recording(recording_file)
            object_reference.fs.program_reset()
            func(*args, **kwargs)
            samples = fs.raw_audio_string(object_reference.fs.get_samples(int(seconds * 44100)))
            object_reference.wav.writeframes(bytes(samples))
            if stop_recording:

                object_reference.wav.close()
                object_reference._start_audio_output()

        elif recording_file is None:

            if not object_reference._audio_driver_is_active:
                object_reference._start_audio_output()

            func(*args, **kwargs)

    return wrapper
