# PyPiano

PyPiano is a python library to programmatically play piano. It is an easy-to-use abstraction layer on top of the
[python-mingus](http://bspaans.github.io/python-mingus/index.html) package providing a simple user interface to play mingus music containers, such as Notes,
NoteContainers, Bars and Tracks. It bundles a default sound fonts file to enable playing and recording audio out
of the box. By default, 8 different pianos are available. It allows playing Piano via audio output or recording music to wav files.

## Installation

For PyPiano to work you need [Fluidsynth](https://www.fluidsynth.org/) to be installed. Please check the
Fluidsynth website on how to install Fluidsynth on your system. Note that you also need to install and set up [git-lfs](https://git-lfs.github.com/)
before installing PyPiano. You then can install PyPiano from Github using pip:

```bash
pip install git+https://github.com/FelixGSE/pypiano.git
```

## Usage

```python
from pypiano import Piano
from mingus.containers import Note

p = Piano()

# Play a simple C-4 via audio
p.play("C-4")

# Play a mingus Note
note = Note("C-4")
p.play(note)

# Record a Note to a wav file
p.play(note, recording_file="my_first_recording.wav", record_seconds=2)

# Use a different instrument
p.load_instrument("Honky-tonk Piano")
p.play(note)
```
The same code works with more complex mingus containers like, NoteContainers, Bars and Tracks


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please make sure to update tests as appropriate.

Note that the sound fonts are checked in as [Git large file](https://git-lfs.github.com/). If you have `git-lfs` installed
the bundled sound font files in `pypiano/sound_fonts/FluidR3_GM.sf2` should be cloned automatically. If not, you should install
`git-lfs` and fetch them after.

## Know issues
The default sound fonts were taken from the [fluid-soundfont](https://packages.debian.org/source/stable/fluid-soundfont) debian package (check `/scripts/get_default_sf_file.py` for details). The file
contains 194 instruments of which only 8 are used within this project, thus making the package unnecessarily large. All 186 unused instruments should be removed
from the shipped sound fonts to reduce package size. It is an open task to find out how to safely remove unused instruments.

## License
- PyPiano is distributed under MIT license - Check corresponding [license file](https://github.com/FelixGSE/pypiano/blob/master/licenses/LICENSE-PyPiano)
- Default sound fonts are distributed under MIT license - Check corresponding [license file](https://github.com/FelixGSE/pypiano/blob/master/licenses/LICENSE-FluidR3_GM_sf2.txt)
