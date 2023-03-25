from contextlib import ExitStack
from pathlib import Path
from tempfile import NamedTemporaryFile

from flacmirror.misc import generate_metadata_block_picture_ogg

from .options import Options
from .processes import (
    FFMPEG,
    AtomicParsley,
    Fdkaac,
    FdkaacUnsupportedSamplerateError,
    ImageMagick,
    Metaflac,
    Oggenc,
    Opusenc,
    VorbisComment,
)


def encode_flac(input_f: Path, output_f: Path, options: Options):
    if options.codec == "opus":
        encode_flac_to_opus(input_f, output_f, options)
    elif options.codec == "vorbis":
        encode_flac_to_vorbis(input_f, output_f, options)
    elif options.codec == "aac":
        encode_flac_to_aac(input_f, output_f, options)
    elif options.codec == "mp3":
        encode_flac_to_mp3(input_f, output_f, options)
    else:
        raise ValueError("Unknown codec")


def encode_flac_to_opus(input_f: Path, output_f: Path, options: Options):
    metaflac = Metaflac(options.debug)
    imagemagick = ImageMagick(options.debug)
    opusenc = Opusenc(options.opus_quality, options.debug)
    pictures_bytes = None
    discard = False
    if options.albumart == "discard":
        discard = True
    elif options.albumart == "keep":
        # We do not need to extract the picture and just let opusenc take
        # them over. This sacrifices a bit of modularity but avoids the
        # extra step of extracting the picture and then reattaching it.
        discard = False
        pictures = None
    elif options.albumart == "optimize" or options.albumart == "resize":
        discard = True
        pictures = None
        image = metaflac.extract_picture(input_f)

        if image is not None:
            if options.albumart == "resize":
                image = imagemagick.optimize_and_resize_picture(
                    image, options.albumart_max_width
                )
            elif options.albumart == "optimize":
                image = imagemagick.optimize_picture(image)

            pictures_bytes = [image]
        else:
            discard = False

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


def encode_flac_to_vorbis(input_f: Path, output_f: Path, options: Options):
    metaflac = Metaflac(options.debug)
    imagemagick = ImageMagick(options.debug)
    oggenc = Oggenc(options.vorbis_quality, options.debug)
    vorbiscomment = VorbisComment(options.debug)
    oggenc.encode(input_f, output_f)
    if options.albumart == "discard":
        return

    image = metaflac.extract_picture(input_f)
    if image is None:
        return
    if options.albumart == "resize":
        image = imagemagick.optimize_and_resize_picture(
            image, options.albumart_max_width
        )
    elif options.albumart == "optimize":
        image = imagemagick.optimize_picture(image)

    block_picture = generate_metadata_block_picture_ogg(image)
    vorbiscomment.add_comment(output_f, "METADATA_BLOCK_PICTURE", block_picture)


def encode_flac_to_aac(input_f: Path, output_f: Path, options: Options):
    metaflac = Metaflac(options.debug)
    imagemagick = ImageMagick(options.debug)
    ffmpeg = FFMPEG(options.debug)
    fdkaac = Fdkaac(options.aac_mode, options.aac_quality, options.debug)
    atomicparsley = AtomicParsley(options.debug)

    caf_content = ffmpeg.encode_caf(input_f)
    try:
        fdkaac.encode_from_mem(caf_content, output_f, None)
    except FdkaacUnsupportedSamplerateError:
        # if we have an unsupported samplerate, resample to 48000 kHz
        caf_content = ffmpeg.resample_caf(caf_content, 48000)
        fdkaac.encode_from_mem(caf_content, output_f, None)

    if options.albumart == "discard":
        return

    image = metaflac.extract_picture(input_f)
    if image is None:
        return
    if options.albumart == "resize":
        image = imagemagick.optimize_and_resize_picture(
            image, options.albumart_max_width
        )
    elif options.albumart == "optimize":
        image = imagemagick.optimize_picture(image)

    with NamedTemporaryFile("wb") as image_file:
        image_file.write(image)
        image_file.flush()
        atomicparsley.add_artwork(output_f, Path(image_file.name))


def encode_flac_to_mp3(input_f: Path, output_f: Path, options: Options):
    metaflac = Metaflac(options.debug)
    imagemagick = ImageMagick(options.debug)
    ffmpeg = FFMPEG(options.debug)
    discard = False
    image = None
    if options.albumart == "discard":
        discard = True
    elif options.albumart == "keep":
        # We do not need to extract the picture and just let opusenc take
        # them over. This sacrifices a bit of modularity but avoids the
        # extra step of extracting the picture and then reattaching it.
        discard = False
    elif options.albumart == "optimize" or options.albumart == "resize":
        discard = True
        image = metaflac.extract_picture(input_f)

        if image is not None:
            if options.albumart == "resize":
                image = imagemagick.optimize_and_resize_picture(
                    image, options.albumart_max_width
                )
            elif options.albumart == "optimize":
                image = imagemagick.optimize_picture(image)
        else:
            discard = False

    ffmpeg.encode_lame(
        input_f, output_f, image, discard, options.mp3_mode, options.mp3_quality
    )
