"""

A simple tool designed to convert extract G1T TEXTURE files into DDS
GitHub: https://github.com/the-real-thunderlol/AOT2-G1T-EXTRACTOR
Version: 0.3
Changes:
- Instead of DX10 for SRGB, use DXT5, nothing is lost and you can see the image in File explorer.

VERSION 0.3, now using information and extraction methodologies used by Raytwo
- better flag detect added
Raytwo GitHub: https://github.com/Raytwo/G1Tool


"""

OUTPUT_FOLDER = "out"

import struct
import os

def show_data(data):
    hex_str = " ".join(f"{b:02x}" for b in data)
    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    print(f"{hex_str}  |  {ascii_str}")


#################################################################################
# DDS header constants
#################################################################################

DDS_MAGIC = b'DDS '

# DDS flags
DDSD_CAPS        = 0x1
DDSD_HEIGHT      = 0x2
DDSD_WIDTH       = 0x4
DDSD_PITCH       = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE  = 0x80000

# Pixel format flags
DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC      = 0x4
DDPF_RGB         = 0x40

# Caps
DDSCAPS_COMPLEX = 0x8
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP  = 0x400000


#################################################################################
# G1T texture type to DDS format mapping
# type byte -> (fourcc, block_size_per_4x4_block)
# for uncompressed: (None, bytes_per_pixel)
#################################################################################

g1t_format_map = {
    0x01: (None,    4),    # BGRA8 uncompressed
    0x02: (None,    4),    # RGBA8 uncompressed
    0x06: (b'DXT1', 8),    # BC1
    0x08: (b'DXT5', 16),   # BC3
    0x09: (b'ATI1', 8),    # BC4
    0x0A: (b'ATI2', 16),   # BC5
    0x10: (b'DXT1', 8),    # BC1
    0x12: (b'DXT5', 16),   # BC3
    0x59: (b'DXT1', 8),    # BC1
    0x5B: (b'DXT5', 16),   # BC3
    0x5C: (b'ATI1', 8),    # BC4
    0x5F: (b'DX10', 16),   # BC7 (requires DX10 header)
}

# DXGI format codes for textures that need DX10 extended header
DXGI_FORMAT_BC7_UNORM = 98

g1t_dxgi_map = {
    0x5F: DXGI_FORMAT_BC7_UNORM,
}


#################################################################################
# DDS functions
#################################################################################

def build_dds(width, height, texture_type, mipmaps):
    if texture_type not in g1t_format_map:
        print(f"Unknown texture type: 0x{texture_type:02X}")
        return None

    fourcc, size_val = g1t_format_map[texture_type]
    is_compressed = fourcc is not None
    use_dx10 = fourcc == b'DX10'

    # flags
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
    caps = DDSCAPS_TEXTURE

    if mipmaps > 1:
        flags |= DDSD_MIPMAPCOUNT
        caps |= DDSCAPS_MIPMAP | DDSCAPS_COMPLEX

    # pitchOrLinearSize
    if is_compressed:
        flags |= DDSD_LINEARSIZE
        pitch_or_linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * size_val
    else:
        flags |= DDSD_PITCH
        pitch_or_linear = width * size_val

    # pixel format (32 bytes)
    if is_compressed:
        pixel_format = struct.pack("<IIIIIIII",
            32, DDPF_FOURCC,
            struct.unpack("<I", fourcc)[0],
            0, 0, 0, 0, 0
        )
    else:
        # uncompressed BGRA8 / RGBA8
        if texture_type == 0x01:  # BGRA
            r_mask, g_mask, b_mask, a_mask = 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000
        else:  # 0x02 RGBA
            r_mask, g_mask, b_mask, a_mask = 0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000

        pixel_format = struct.pack("<IIIIIIII",
            32, DDPF_RGB | DDPF_ALPHAPIXELS,
            0,   # no fourcc
            32,  # 32 bits per pixel
            r_mask, g_mask, b_mask, a_mask
        )

    # reserved (11 ints = 44 bytes)
    reserved = b'\x00' * 44

    # main header (124 bytes)
    header = struct.pack("<IIIIIII",
        124,                # dwSize
        flags,              # dwFlags
        height,             # dwHeight
        width,              # dwWidth
        pitch_or_linear,    # dwPitchOrLinearSize
        0,                  # dwDepth
        mipmaps,            # dwMipMapCount
    )
    header += reserved
    header += pixel_format
    header += struct.pack("<IIIII",
        caps,               # dwCaps
        0,                  # dwCaps2
        0, 0, 0             # dwCaps3, dwCaps4, dwReserved2
    )

    result = DDS_MAGIC + header

    # apparently there are a billion types of ways textures are written.
    # claude add DX10 extended header for formats with no legacy FourCC (e.g. BC7)
    if use_dx10 and texture_type in g1t_dxgi_map:
        dx10_header = struct.pack("<IIIII",
            g1t_dxgi_map[texture_type],
            3,              # D3D10_RESOURCE_DIMENSION_TEXTURE2D
            0,              # miscFlag
            1,              # arraySize
            0               # miscFlags2
        )
        result += dx10_header

    return result


def convert_raw_image_data(pixel_data, width, height, texture_type, mipmaps):
    header = build_dds(width, height, texture_type, mipmaps)
    if header is None:
        return None
    return header + pixel_data


def save_as_dds(pixel_data, width, height, texture_type, mipmaps, output_path):
    dds_data = convert_raw_image_data(pixel_data, width, height, texture_type, mipmaps)
    if dds_data is None:
        return False

    with open(output_path, "wb") as out:
        out.write(dds_data)

    return True


#################################################################################
# G1T extraction
#################################################################################

def g1t_extract(INPUT_PATH, OUTPUT_FOLDER):
    #os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    ##OUTPUT_FOLDER = os.path.splitext(INPUT_PATH)[0]

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(INPUT_PATH, "rb") as file:

        # G1T header (28 bytes)
        magic = file.read(4)
        version = file.read(4)
        print(f"        Magic Bytes: {magic}")
        print(f"            Version: {version}")

        data = file.read(20)
        total_size, offset_table_address, total_textures, unknown, pad1 = struct.unpack("<IIIII", data)
        print(f"Total size in bytes: {total_size}")
        print(f"    Offset Table at: {offset_table_address}")
        print(f"     Total Textures: {total_textures}")
        print(f" Something not used: {unknown} - ????")

#################################################################################
        # # normal map flags table
        # texture_number = 1
        # n = 0
        for x in range(0, total_textures):
            data = file.read(4)
        #
        #     ### not really used anywhere other than internally to define what kind of texture each file is
        #     if data == b'\x00\x00\x00\x00':
        #         print(f"\nTexture {texture_number}")
        #         print(f"{n} - Texture: ", end="")
        #         texture_number = texture_number + 1
        #     elif data == b'\x03\x00\x00\x00':
        #         print(f"{n} - Normal: ", end="")
        #     elif data == b'\x02\x00\x00\x00':
        #         print(f"{n} - Mipmap: ", end="")
        #     elif data == b'\x04\x00\x00\x00':
        #         print(f"{n} - Noise: ", end="")
        #     else:
        #         print(f"{n} - Unknown (0x{struct.unpack('<I', data)[0]:08X}): ", end="")
        #
        #     n = n + 1
        #     show_data(data)

#################################################################################
        ### GET OFFSETS OF FILES
        offsets = []

        for y in range(0, total_textures):
            data = file.read(4)
            # convert to little endian
            relative_offset = struct.unpack("<I", data)[0]

            ### offsets are relative to offset_table_address
            offsets.append(offset_table_address + relative_offset)

#################################################################################
        # extract files
        for z in range(0, total_textures):
            file.seek(offsets[z])

            # base header (8 bytes)
            base_header = file.read(8)

            mipmap_byte = base_header[0]
            texture_type = base_header[1]
            dim_byte = base_header[2]
            flags = struct.unpack_from("<I", base_header, 4)[0]

            # get last 4 bits
            dimension_right = dim_byte & 0x0F
            # get the first 4 bits
            dimension_left = dim_byte >> 4

            mipmap_count = mipmap_byte >> 4
            width = 2 ** dimension_right
            height = 2 ** dimension_left

            # check for extra header
            skip = 8
            is_srgb = False

            if (flags >> 24) & 0x10:
                # first uint32 after base header is the extra header size
                extra_header_size = struct.unpack("<I", file.read(4))[0]
                extra_remaining = file.read(extra_header_size - 4)

                # last 4 bytes of extra header contain sRGB flag
                if len(extra_remaining) >= 4:
                    extra_unk = struct.unpack("<I", extra_remaining[-4:])[0]
                    if (extra_unk >> 24) == 0x01:
                        is_srgb = True

                skip = 8 + extra_header_size

            print(f"{z}: {width}x{height} type=0x{texture_type:02X} mipmaps={mipmap_count} srgb={is_srgb} skip={skip}")

            # read full texture entry
            file.seek(offsets[z])
            if z < total_textures - 1:
                texture_size = offsets[z + 1] - offsets[z]
            else:
                texture_size = total_size - offsets[z]

            texture_data = file.read(texture_size)

            save_as_dds(
                texture_data[skip:],
                width, height, texture_type, mipmap_count,
                os.path.join(OUTPUT_FOLDER, f"texture_{z}.dds")
            )


def folder_extract(INPUT_FOLDER_PATH, file_starts_with="chunk"):
    """Basically give the whole folder as a whole and extract files if exist"""

    ### get all files in the selected directory, even if not all are G1T
    files = len(os.listdir(INPUT_FOLDER_PATH))

    for id in range(0,files):
        INPUT_PATH = f"{INPUT_FOLDER_PATH}/{file_starts_with}_{id}.g1t"
        OUTPUT_FOLDER = f"{INPUT_FOLDER_PATH}/g1t/{file_starts_with}_{id}/"

        if os.path.exists(INPUT_PATH):
            g1t_extract(INPUT_PATH, OUTPUT_FOLDER)

        else:
            print(f"{id}: False")
            pass
