"""
Code was inspired from Cathleann G1M extract.
Code to extract G1M was converted into python.

Credits: neptuwunium
GitHub: https://github.com/neptuwunium/Cethleann/blob/develop/Cethleann/Graphics/G1Model.cs  # exact file
"""

import os
import struct

# using it alot; not to future self, move this into a function file
def read_uint32_le(file):
    return struct.unpack("<I", file.read(4))[0]

def extract_g1m_containers(G1M_CONTAINER, OUTPUT_DIR):
    chunk_name = os.path.splitext(os.path.basename(G1M_CONTAINER))[0]

    with open(G1M_CONTAINER, "rb") as file:

        # read first 2 fields: entry count and header size
        entry_count         = read_uint32_le(file)  # n: entries [2] to [n] are g1m offsets
        wrapper_header_size = read_uint32_le(file)  # total header size in bytes

        # read g1m offsets: (entry_count - 1) offsets starting at [2]
        g1m_count = entry_count - 1
        g1m_offsets = []
        for i in range(g1m_count):
            g1m_offsets.append(read_uint32_le(file))

        print(f"  entry_count={entry_count}, header={wrapper_header_size}, g1m_count={g1m_count}")

        # extract each g1m
        chunk_OUTPUT_DIR = f"{OUTPUT_DIR}/{chunk_name}"
        os.makedirs(chunk_OUTPUT_DIR, exist_ok=True)

        for i, g1m_offset in enumerate(g1m_offsets):
            if g1m_offset == 0:
                continue

            file.seek(g1m_offset)
            magic_bytes = file.read(4)

            if magic_bytes != b"_M1G":
                print(f"  SKIP [{i}]: no _M1G at offset {g1m_offset}")
                continue

            file.read(4)  # version string ("6300", "7300"), skipped
            resource_section_size = read_uint32_le(file)

            file.seek(g1m_offset)
            g1m_blob = file.read(resource_section_size)

            g1m_output_path = f"{chunk_OUTPUT_DIR}/{chunk_name}_{i}.g1m"
            with open(g1m_output_path, "wb") as output_file:
                output_file.write(g1m_blob)

            print(f"  {chunk_name}_{i}.g1m  ({len(g1m_blob)} bytes)")

def extract_g1m_containers_in_folder(input_dir, OUTPUT_DIR="g1m/"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    wrapped_g1m_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".g1m")])
    print(f"Found {len(wrapped_g1m_files)} files in {input_dir}\n")

    for wrapped_filename in wrapped_g1m_files:
        G1M_CONTAINER = f"{input_dir}/{wrapped_filename}"
        print(f"{wrapped_filename}:")
        extract_g1m_containers(G1M_CONTAINER, OUTPUT_DIR)

    print(f"\nDone. Output in {OUTPUT_DIR}")



