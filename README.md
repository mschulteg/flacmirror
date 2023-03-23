# flacmirror

[![PyPI - Version](https://img.shields.io/pypi/v/flacmirror)](https://pypi.org/project/flacmirror/)

`flacmirror` is a cli tool that recursively synchronizes a directory containing flac files
to another directory while encoding the flac files to a specified format instead of copying them.

## Information

The supported target formats are vorbis, opus, mp3 (lame) and aac (LC profile).
This tool has limited customizability. You can find more powerful solutions on github like flac2all.

Except for quality parameters, flacmirror will not specify any other encoding parameters when calling
the encoding tools. Therefore most encoding settings will depend on the encoding tools' defaults.

## Examples

Convert and sync directory Music_FLAC/ to Music_OPUS/ while keeping the embedded artwork untouched.
Only overwrite output files, if input files changed. Also specify the opus target bitrate to be
96 kbit/s.

``` bash
flacmirror Music_FLAC/ Music_OPUS/ --codec opus --opus-quality 96 --albumart keep
```

Convert/sync directory Music_FLAC/ to Music_MP3/ and optimize embedded album art in the output
files (default). Overwrite all output files (re-encode everything). Also delete files in the
target directory, which are not in the input directory. The target mp3 files hould have VBR V0 quality.

``` bash
flacmirror Music_FLAC/ Music_MP3/ --codec mp3 --mp3-mode vbr --mp3-quality 0 --overwrite all --delete
```

Convert/sync and resize all embedded cover art wider than 500px to 500px width in the output files.

``` bash
flacmirror Music_FLAC/ Music_OGG/ --codec vorbis --albumart resize --album-art-max-width 500
```

Convert/sync and discard embedded album art in output files. Also copy files with the name
`folder.jpg` and `cover.jpg` to the output directory.

``` bash
flacmirror Music_FLAC/ Music_OGG/ --codec vorbis --albumart discard --copy-file folder.jpg --copy-file cover.jpg
```

Convert/sync using 4 threads (default number is the number of available threads in the system). ALso copy
files with the `.jpg` extension to the output directory.

``` bash
flacmirror Music_FLAC/ Music_AAC/ --codec aac --acc-mode 5 --copy-ext jpg --num-threads 4
```

## Dependencies
### Python

Python >= 3.7

No libraries required

### Installed programs

- `metaflac` (required)

- `convert (imagemagick)` (required for --albumart {optimize,resize})

- `oggenc` (required for vorbis encoding)

- `vorbiscomment` (required for vorbis encoding)

- `opusenc` (required for opus encoding)

- `fdkaac` (required for aac encoding)

- `ffmpeg` (required for mp3 encoding and aac metadata handling)

## Installation

Install using pip or pipx.

```bash
pip install flacmirror
```

Download the wheel found under Releases and install it using pip.

```bash
pip install flacmirror-X.X.X-py3-none-any.whl
```

This will install the executable `flacmirror` to one of your bin folders (global, user or venv)
which then should usually be available in your path.

## Misc
### Album art optimization

The option `--albumart optimize` is set by default and will try to convert all albumart
to stripped and optimized jpeg files.
This should result in smaller albumart sizes without compromising too much on quality.
This means that cover art will be extracted from the source flac file and embedded into the output file
after being piped through the following command, which can currently not be customized.

```bash
convert - -strip -interlace Plane -sampling-factor 4:2:0 -colorspace sRGB -quality 85% jpeg:-
```

If the option `--albumart resize` is set , the following command is used to optimize and downscale
pictures that are wider than `ALBUMART_MAX_WIDTH` pixels, which is specified by `--albumart-max-width`.

```bash
convert - -strip -interlace Plane -sampling-factor 4:2:0 -colorspace sRGB -resize ${ALBUMART_MAX_WIDTH}\> -quality 85% jpeg:-
```


## Usage

```
usage: flacmirror [-h] [--codec {vorbis,opus}] [--opus-quality OPUS_QUALITY] [--vorbis-quality VORBIS_QUALITY]
                  [--albumart {optimize,resize,keep,discard}] [--albumart-max-width ALBUMART_MAX_WIDTH]
                  [--overwrite {all,none,old}] [--delete] [--yes] [--copy-file COPY_FILE] [--copy-ext COPY_EXT]
                  [--num-threads NUM_THREADS] [--dry-run] [--debug] [--version]
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
  --codec {vorbis,opus,aac,mp3}              Specify which target codec to use.
  --opus-quality OPUS_QUALITY                If opus encoding is selected, the bitrate in kbit/s can be specified as a
                                             float. The value is directly passed to the --bitrate argument of opusenc.
  --vorbis-quality VORBIS_QUALITY            If vorbis encoding is selected, the quality can be specified as an integer
                                             between -1 and 10. The value is directly passed to the --quality argument
                                             of oggenc.
  --aac-quality AAC_QUALITY                  If aac encoding is selected and aac-mode is set to 0 (CBR), the bitrate in
                                             kbit/s can be specified as an integer. The value is directly passed to the
                                             --bitrate argument of fdkaac. Defaults to 128 (kbit/s).
  --aac-mode AAC_MODE                        If aac encoding is selected, the bitrate configuration mode of fdkaac can
                                             be specified as an integer from 0 to 5, where 0 means CBR (default) and 1-5
                                             means VBR (higher value -> higher bitrate). The value is directly passed to
                                             the --bitrate-mode argument of fdkaac.
  --mp3-quality MP3_QUALITY                  If mp3 encoding is selected and --mp3-mode is set to cbr or abr, this sets
                                             the bitrate in kbit/s as an integer from 8 to 320. If --mp3-mode is set to
                                             vbr, this sets the quality level integer from 0 to 9 (like the V of lame or
                                             q:a settings of ffmpeg).
  --mp3-mode {vbr,cbr,abr}                   If mp3 encoding is selected, this specified the quality mode to be used. If
                                             specified, --mp3-quality must also be set to a valid value. If not
                                             specified, ffmpeg will use default values for mode and quality.
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
                                             changed since (the source file's modification date is newer). Defaults to
                                             'old'.
  --delete                                   Delete files that exist at the destination but not the source.
  --yes, -y                                  Skip any prompts that require you to press [y] (--delete)
  --copy-file COPY_FILE                      Copy additional files with filename COPY_FILE that are not being encoded.
                                             This option can be used multiple times. For example --copy-file cover.jpg
                                             --copy-file album.jpg
  --copy-ext COPY_EXT                        Copy additional files with the extension COPY_EXT that are not being
                                             encoded. This option can be used multiple times. For example --copy-ext m3u
                                             --copy-ext log --copy-ext jpg. This will not copy flac files.
  --num-threads NUM_THREADS                  Number of threads to use. Defaults to the number of threads in the system.
  --dry-run                                  Do a dry run (do no copy, encode, delete any file)
  --debug                                    Give more output about how subcommands are called
  --version                                  show program's version number and exit
```

## Limitations

Currently there are some limitations.
- Only one album art entry is extracted and then interpreted as TYPE 3: Cover(front)
- Additional encoding parameters can not be specified
