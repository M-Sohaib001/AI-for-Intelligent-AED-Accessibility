import hashlib

with open("scdf_aed_frozen.geojson", "rb") as f:
    checksum = hashlib.sha256(f.read()).hexdigest()

with open("scdf_aed_frozen.sha256", "w") as f:
    f.write(checksum)

print(checksum)