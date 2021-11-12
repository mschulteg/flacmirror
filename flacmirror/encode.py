from pathlib import Path
from tempfile import NamedTemporaryFile
from contextlib import ExitStack

from .options import Options
from .processes import (
    ImageMagick,
    Metaflac,
    Opusenc,
)


def encode_flac(input_f: Path, output_f: Path, options: Options):
    metaflac = Metaflac()
    imagemagick = ImageMagick()
    opusenc = Opusenc()
    pictures_bytes = None
    discard = False
    if options.albumart == "discard":
        discard = True
    elif options.albumart == "keep":
        discard = False
        pictures = None
    elif options.albumart == "optimize" or options.albumart == "resize":
        discard = True
        pictures = None
        image = metaflac.extract_picture(input_f)
        if options.albumart == "resize":
            image = imagemagick.optimize_and_resize_picture(
                image, options.albumart_max_width
            )
        elif options.albumart == "optimize":
            image = imagemagick.optimize_picture(image)

        pictures_bytes = [image]

    with ExitStack() as stack:
        if pictures_bytes is not None:
            # Create temporary files since opusenc only accepts pictures
            # as paths. The tempfiles are automaticlly deleted when going
            # out of context.
            tempfiles = []
            for picture in pictures_bytes:
                tempfile = stack.enter_context(NamedTemporaryFile("wb"))
                tempfile.write(picture)
                tempfile.flush()
                tempfiles.append(tempfile)
            pictures = [Path(tempfile.name) for tempfile in tempfiles]
        else:
            pictures = None
        opusenc.encode(input_f, output_f, discard, pictures)
