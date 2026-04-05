import struct
import os
from custom_libraries import linkdata_extract,popup,g1t_extractor, extract_g1m


import time

start_time = time.time()  # start timer
### select file
# FILE = popup.select_file([
#      ("BIN FILES", "*.BIN")
# ])

FILE = "LINKDATA_A.BIN"

### after selection, select output folder
# OUTPUT = popup.select_folder()
OUTPUT = "output/"
os.makedirs(OUTPUT, exist_ok=True)

### extract toc
TOC = linkdata_extract.make_toc(FILE,OUTPUT)

linkdata_extract.extract_files(FILE,OUTPUT,TOC)
linkdata_extract.decompress_files(OUTPUT,TOC)
linkdata_extract.assign_extensions(OUTPUT, TOC)

# git_extractor can go throught the entire directory or a single file

g1t_extractor.folder_extract(OUTPUT)

extract_g1m.extract_g1m_containers_in_folder(OUTPUT)


end_time = time.time()  # end timer
print(f"Execution time: {end_time - start_time:.3f} seconds")
