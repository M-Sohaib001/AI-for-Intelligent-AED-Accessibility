import hashlib
import os

file_path = "data/raw/scdf_aed_frozen.geojson"
if not os.path.exists(file_path):
    print(f"Error: {file_path} not found!")
    exit(1)

with open(file_path, "rb") as f:
    checksum = hashlib.sha256(f.read()).hexdigest()

with open("data/scdf_aed_frozen.sha256", "w") as f:
    f.write(checksum)

print(f"Checksum saved: {checksum}")