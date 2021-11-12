import struct
import base64

def generate_metadata_block_picture(data: bytes) -> str:
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
    data_base64 = base64.b64encode(header + data).decode()
    return f"METADATA_BLOCK_PICTURE={data_base64}"
