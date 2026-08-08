import requests

dataset_id = "d_4e6b82c58a8a832f6f1fee5dfa6d47ea"

url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

response = requests.get(url)
json_data = response.json()

if json_data["code"] != 0:
    raise RuntimeError(json_data["errMsg"])

download_url = json_data["data"]["url"]

geojson_bytes = requests.get(download_url).content

with open("scdf_aed_frozen.geojson", "wb") as f:
    f.write(geojson_bytes)

print(f"Downloaded {len(geojson_bytes)} bytes")