# Information
`flacmirror` is a cli tool that recursively synchronizes a directory containing flac files
to another directory while encoding the flac files to a specified format instead of copying them.

The supported target formats are vorbis and opus.

This is a small side project, you can find more powerful solutions on github like flac2all.

# Dependencies
## Python

Python >= 3.6

No libraries required

## Installed programs
- `metaflac` (required)

- `convert (imagemagick)` (required for --albumart {optimize,resize})

- `oggenc` (required for vorbis encoding)

- `vorbiscomment` (required for vorbis encoding)

- `opusenc` (required for opus encoding)

# Installation

For now, the easiest way is to clone the project and install the
package using pip.

```bash
pip clone https://github.com/mschulteg/flacmirror.git
cd flacmirror
pip install .
```

This will install the executable `flacmirror` to one of your bin folders (global, user or venv)
which then should usually be available in your path.

# Usage
```
usage: flacmirror [-h] [--codec {vorbis,opus}] [--opus-quality OPUS_QUALITY] [--vorbis-quality VORBIS_QUALITY]
                  [--albumart {optimize,resize,keep,discard}] [--albumart-max-width ALBUMART_MAX_WIDTH]
                  [--overwrite {all,none,old}] [--delete] [--yes] [--copy-files COPY_FILES] [--num-threads NUM_THREADS]
                  [--dry-run] [--version]
                  src_dir dst_dir

Program to recursively synchronize a directory containing flac files to another directory while encoding the flac files
instead of copying them.

positional arguments:
  src_dir                                    The source directory. This directory will be recursively scanned for flac
                                             files to be encoded.
  dst_dir                                    The destination directory. Encoded files will be saved here using the same
                                             directory structure as in src_dir.

optional arguments:
  -h, --help                                 show this help message and exit
  --codec {vorbis,opus}                      Specify which target codec to use.
  --opus-quality OPUS_QUALITY                If opus encoding was selected, the bitrate in kbit/s can be specified as a
                                             float. The value is direclty passed to the --bitrate argument of opusenc.
  --vorbis-quality VORBIS_QUALITY            If vorbis encoding was selected, the quality can be specified as an integer
                                             between -1 and 10. The value is directly passed to the --quality argument
                                             of oggenc.
  --albumart {optimize,resize,keep,discard}  Specify what to do with album covers. Defaults to 'optimize'. 'optimize'
                                             will try to optimize the picture for better size, while 'resize' will
                                             additionally downsample pictures with a pixel width greater than
                                             --albumart-max-width (default 750) while scaling the height proportionally.
                                             'keep' will just copy the album art over to the new file, while 'discard'
                                             will not add the album art to the encoded file.
  --albumart-max-width ALBUMART_MAX_WIDTH    Specify the width in pixels to which album art is downscaled to (if
                                             greater). Defaults to 750. Only used when --albumart is set to resize.
  --overwrite {all,none,old}                 Specify if or when existing files should be overwritten. 'all' means that
                                             files are always overwritten, 'none' means that files are never overwritten
                                             and 'old' means that files are only overwritten if the source file has
                                             changed since (the source file's modification date is newer).
  --delete                                   Delete files that exist at the destination but not the source.
  --yes, -y                                  Skip any prompts that require you to press [y] (--delete)
  --copy-files COPY_FILES                    Copy additional files that are not being encoded. COPY_FILES is a list of
                                             filenames separated by ','. For example --copy-files
                                             "cover.jpg,albumart.jpg"
  --num-threads NUM_THREADS                  Number of threads to use. Defaults to the number of threads in the system.
  --dry-run                                  Do a dry run (do no copy, encode, delete any file)
  --version                                  show program's version number and exit
```

# Limitations
Currently there are some limitations.
- Only supported codecs are vorbis and opus
- Only one album art entry is extracted and then interpreted as TYPE 3: Cover(front)