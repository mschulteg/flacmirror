# Changelog

## v0.3.1 - 2023-03-25
### Fixed
- Resample audio files if their samplerate is not supported by fdkaac.

## v0.3.0 - 2023-03-23
### Added
- MP3 support (using ffmpeg with libmp3lame as an encoder)
- AAC support (using fdkaac as an encoder)
- New example section in readme

## v0.2.4 - 2022-09-08
### Changed
- Fix readme showing wrong python version
- Switch to using hatch for project management
- Release on pypi

### Added
- Make flacmirror work with the python -m flag

## v0.2.3 - 2022-07-02
### Changed
- Add CI, nothing changed for flactools itself

## v0.2.2 - 2022-06-28
### Fixed
- Set the correct minimum python version to 3.7 instead of 3.6

## v0.2.1 - 2022-06-17
### Changed
- Change output file extension from .ogg to .opus for opus encoded files
  Some media players do not seem to like like the .ogg extension for opus audio files
  and the .opus extension is also [recommended](https://datatracker.ietf.org/doc/html/rfc7845#section-9).
- To fix (recursively rename files from ogg to opus) already synced directories you can use the
  following command under linux:
  ```bash
  find . -name '*.ogg' -exec rename .ogg .opus {} +
  ```

## v0.2.0 - 2021-11-24
### Added
- Add --copy-ext option

## v0.1.1 - 2021-11-16
### Fixed
- Fix convert command using wrong target color format