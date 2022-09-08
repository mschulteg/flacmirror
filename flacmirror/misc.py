import base64
import datetime
import struct


def generate_metadata_block_picture(data: bytes) -> bytes:
    # assume jpeg tag and empty description, use picturetype 3 for cover(front)
    int_picturetype = 3
    str_mime = b"image/jpeg"
    str_description = b""
    int_width = 0
    int_height = 0
    int_depth = 0
    int_index = 0

    header = struct.pack(
        f">II{len(str_mime)}sI{len(str_description)}sIIIII",
        int_picturetype,
        len(str_mime),
        str_mime,
        len(str_description),
        str_description,
        int_width,
        int_height,
        int_depth,
        int_index,
        len(data),
    )
    return header + data


def generate_metadata_block_picture_ogg(data: bytes) -> str:
    block_picture = generate_metadata_block_picture(data)
    return base64.b64encode(block_picture).decode()


def format_date(t: datetime.timedelta) -> str:
    days = t.days
    hours, remainder = divmod(t.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    units = {"days": days, "hours": hours, "minutes": minutes, "seconds": seconds}
    unit_strs = []
    for name, value in units.items():
        if value != 0 or name == "seconds":
            unit_strs += [f"{value} {name}"]
    return ", ".join(unit_strs)
