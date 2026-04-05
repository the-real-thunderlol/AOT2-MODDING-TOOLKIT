import struct
import os
import csv
import zlib
import threading

########################
"""
processes to run, recommended for 4 on Gen 3 NVME's. There is too much RW operations performing.
you lose performance if you add more threads
"""

USE_CORES = 4
CORE_OVERRIDE = True

if (CORE_OVERRIDE == True):
    # also verify if you have that many avaliable for processing
    if os.cpu_count() >= USE_CORES:
        CORES = USE_CORES
    else:
        print(f"Insufficient amount of threads avaliable than override. Using {os.cpu_count()} threads instead.")
        CORES = os.cpu_count()
else:
    CORES = os.cpu_count()


########################

def assign_extensions(OUTPUT_PATH, TOC_FILE):
    ### toc is only needed to get "entries" in file. You can bypass it by manually providing the value
    with open(TOC_FILE, "r") as toc_file:
        reader = csv.reader(toc_file)
        row = next(reader)

        total_entries = int(row[1])

    ### close toc, we have the data we need

    for entry in range(0,total_entries):
        try:
            with open(f"{OUTPUT_PATH}/chunk_{entry}.bin", "rb") as chunk:
                signature = chunk.read(4)
                signature_4 = signature[:4]
                #signature_32_4 = signature[32:36]
                if len(signature) >= 4: ## confirm if not empty
                    if signature_4 == b"\x5f\x53\x32\x47":  # _S2G
                        extension = "s2g"
                    elif signature_4 == b"\x44\x58\x42\x43":  # DXBC direct x somehting
                        extension = "dxbc"
                    elif signature_4 == b"\x47\x54\x31\x47":  # GT1G texture files
                        extension = "g1t"
                    elif signature_4 == b"\x54\x4c\x53\x4b":  # TLSK
                        extension = "tlsk"
                    elif signature_4 == b"\x4c\x43\x53\x4b":  # LCSK
                        extension = "lcsk"
                    elif signature_4 == b"\x4d\x44\x4c\x53":  # MDLS model files
                        extension = "mdls"
                    elif signature_4 == b"\x48\x49\x55\x42":  # HIUB
                        extension = "hiub"
                    elif signature_4 == b"\x48\x57\x59\x58":  # HWYX
                        extension = "hwyx"
                    elif signature_4 == b"\x4d\x45\x31\x47":  # ME1G
                        extension = "me1g"
                    elif signature_4 == b"\x46\x50\x31\x47":  # FP1G
                        extension = "fp1g"
                    elif signature_4 == b"\x4b\x54\x53\x52":  # KTSR
                        extension = "ktsr"
                    elif signature_4 == b"\x41\x54\x53\x4c":  # ATSL
                        extension = "atsl"
                    elif signature_4 == b"\x5f\x4f\x4c\x53":  # _OLS level of detail
                        extension = "ols"
                    elif signature_4 == b"\x4b\x54\x53\x43":  # KTSC
                        extension = "ktsc"
                    else:
                        extension = "bin"

                    # if none above, might be g1m, due to complexity read seperately

                    if extension == "bin":
                        # 27th March 2026
                        # literally just check 4 bytes
                        chunk.read(4) #skip 4
                        try:
                            data = chunk.read(4)
                            le_data = struct.unpack("<I", data) # or basically first offset
                            print(le_data)
                            chunk.seek(le_data[0])

                            signature = chunk.read(4)
                            signature_4 = signature[:4]

                            if signature_4 == b"\x5f\x4d\x31\x47": # _M1G (G1M model files)
                                extension = "g1m"
                            else:
                                extension = "bin"
                        except struct.error: #likely 00 00 00 00
                            extension = ""
                            print(f"error {entry}")


                else:
                    extension = ""

            os.rename(
                f"{OUTPUT_PATH}/chunk_{entry}.bin",
                f"{OUTPUT_PATH}/chunk_{entry}.{extension}"
            )

            print(f"{entry} : {signature}")

        except FileNotFoundError:
            print(f"Skipping entry {entry}")

    print(total_entries)

def decompress_files(OUTPUT_PATH, TOC_FILE):
    ZLIB_SECOND_BYTES = {0x01, 0x5e, 0x9c, 0xda}

    try:
        f = open(TOC_FILE)
        f.close()
    except FileNotFoundError:
        print("File Not Found")
        return 0

    with open(TOC_FILE, "r") as toc:
        reader = csv.reader(toc)
        row = next(reader)

        code = row[0]  # 491001
        file_entries = int(row[1])

        ## check if first entry is 491001
        if code == "491001":
            print("TOC was OF BIN FILE")

            work_items = []

            for entries in range (0, file_entries):

                # read entries
                row = next(reader)

                compressed_size   = int(row[2])
                decompressed_size = int(row[3])

                if decompressed_size == 0: ### skip decompression for non-compressed files
                    print(f"Skip file {entries}")
                    continue
                else:
                    CHUNK_PATH = f"{OUTPUT_PATH}/chunk_{entries}.bin"
                    work_items.append((entries, CHUNK_PATH))

            def decompress_chunk(entry, CHUNK_PATH):
                with semaphore:
                    print(f"Working on file {entry}")
                    ## load data

                    with open(CHUNK_PATH, "rb") as chunk_file:
                        data = chunk_file.read()

                    ## start extracting
                    chunk_offsets = []
                    offset = 0

                    while offset < len(data) - 1:
                        pos = data.find(b'\x78', offset)
                        if pos == -1 or pos >= len(data) - 1:
                            break

                        if data[pos + 1] in ZLIB_SECOND_BYTES and (0x78 * 256 + data[pos + 1]) % 31 == 0:
                            try:
                                decoded = zlib.decompressobj()
                                decoded.decompress(data[pos:pos + 256])
                                chunk_offsets.append(pos)
                                offset = pos + 2
                            except zlib.error:
                                offset = pos + 1
                        else:
                            offset = pos + 1

                    chunks = []

                    for i, start in enumerate(chunk_offsets):
                        end = chunk_offsets[i + 1] if i + 1 < len(chunk_offsets) else len(data)
                        decoded = zlib.decompressobj()
                        try:
                            chunks.append(decoded.decompress(data[start:end]))
                        except zlib.error:
                            pass

                    combined_data = b"".join(chunks)

                    with open(CHUNK_PATH, "wb") as write_file:
                        write_file.write(combined_data)

            ####
            TOTAL_CORES = CORES
            semaphore = threading.Semaphore(TOTAL_CORES) ## total tasks at a time

            workloads = []
            for entry, CHUNK_PATH in work_items:
                task_n = threading.Thread(target=decompress_chunk, args=(entry, CHUNK_PATH))
                workloads.append(task_n)
                task_n.start()

            for task_n in workloads:
                task_n.join()

        else:
            print("TOC was NOT OF BIN FILE")

def extract_files(INPUT_FILE, OUTPUT_PATH, TOC_FILE):
    ### check if file exists
    try:
        f = open(TOC_FILE)
        f.close()
    except FileNotFoundError:
        print("File not found.")
        return 0

    print(f"TOC Exists: {TOC_FILE}")

    with open(TOC_FILE, "r") as toc:
        reader = csv.reader(toc)
        row = next(reader)

        code              = row[0] # 491001
        file_entries      = int(row[1])
        offset_multiplier = int(row[2])

        ## check if first entry is 491001
        if code == "491001":
            print("IS A BIN FILE")

            ## build work list from TOC for threading
            work_items = []

            ## start extracting files
            for entry in range(0,file_entries):
                ## read next row in toc
                row = next(reader)

                entry_start_offset      = int(row[0])
                entry_file_size         = int(row[2])

                ## get where the file starts
                start_byte = entry_start_offset * offset_multiplier

                work_items.append((entry, start_byte, entry_file_size))

            def extract_chunk(entries, start_byte, entry_file_size):
                with semaphore:
                    with open(INPUT_FILE, "rb") as file:
                        ## goto start_byte in LINKDATA
                        file.seek(start_byte)

                        ## get chunk size
                        chunk = file.read(entry_file_size)

                        with open(f"{OUTPUT_PATH}/chunk_{entries}.bin","wb") as out:
                            out.write(chunk)

            ## start threads
            TOTAL_CORES = CORES
            semaphore = threading.Semaphore(TOTAL_CORES)  ## total tasks at a time

            tasks = []
            for entry, start_byte, entry_file_size in work_items:
                task_n = threading.Thread(target=extract_chunk, args=(entry, start_byte, entry_file_size))
                tasks.append(task_n)
                task_n.start()

            for task_n in tasks:
                task_n.join()

        else:
            print("NOT A LINKDATA.BIN FILE")
            return 0

def make_toc(INPUT_FILE, OUTPUT_PATH):
    TOC_PATH = f"{OUTPUT_PATH}/toc"

    try:
        os.makedirs(TOC_PATH)
    except FileExistsError:
        pass

    TOC_FILE = f"{TOC_PATH}/toc.csv"

    with open(INPUT_FILE, "rb") as file, open(TOC_FILE, "w", newline="") as WRITE_TOC_FILE:

        ### read the first 16 header bytes
        data = file.read(16)

        little_endian_data = struct.unpack("<IIII", data[:16])

        code              = little_endian_data[0] # 490001
        file_entries      = little_endian_data[1]
        offset_multiplier = little_endian_data[2]
        padding           = little_endian_data[3]

        print(f"There are {file_entries} entries in this BIN container.")

        ### write csv

        writer = csv.writer(WRITE_TOC_FILE)
        writer.writerow([code, file_entries, offset_multiplier, padding])

        ### after that read the next "file" entry bytes:

        for x in range (0, file_entries):
            data = file.read(16)
            little_endian_data = struct.unpack("<IIII", data[:16])

            entry_start_offset      = little_endian_data[0]
            entry_padding           = little_endian_data[1]
            entry_compressed_size   = little_endian_data[2]
            entry_decompressed_size = little_endian_data[3]

            writer.writerow([entry_start_offset, entry_padding, entry_compressed_size, entry_decompressed_size])

    ## after work done, return path
    return TOC_FILE

#assign_extensions("../outA", "../outA/toc/toc.csv")