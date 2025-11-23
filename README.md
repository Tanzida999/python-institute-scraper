# Nearby Institutes Scraper

A small Python script that finds nearby institutes (schools, colleges, universities, training centers, libraries) using OpenStreetMap's Nominatim (geocoding) and Overpass APIs. The script extracts the name, address (when available), phone number (when present in OSM tags), and coordinates, and writes results to CSV or JSON.

**Requirements**

- Python 3.8+
- `requests` library

Install the dependency:

```powershell
pip install requests
```

**Files**

- `web-scraping/scrap.py` — main scraper script

**Usage**

Run the script from the repository root. Examples (PowerShell):

```powershell
# Geocode 'Cambridge, MA' and save CSV
python .\web-scraping\scrap.py --location "Cambridge, MA" --radius 3000 --output results.csv

# Same, but save JSON
python .\web-scraping\scrap.py -l "Cambridge, MA" -r 3000 -o results.json -f json

# Use IP-based location fallback and default radius (2000m)
python .\web-scraping\scrap.py -r 2000 -o near_me.csv
```

**Output**

- CSV fields: `name`, `address`, `phone`, `lat`, `lon`
- JSON: array of objects with `name`, `address`, `phone`, `lat`, `lon`, and raw `tags` from OSM

**Notes & Limitations**

- The script uses the public Nominatim and Overpass endpoints. Respect their usage policies and avoid sending heavy automated traffic. For high-volume or commercial use consider paid APIs or hosting your own Overpass/Nominatim instance.
- OSM data varies by region — phone numbers and address components may be missing or incomplete.
- Network access is required to run the script.

**Next steps**

- If you want, I can add a `requirements.txt`, run the script for a sample location, or extend the POI filters to include other types of institutes.

**Credits**

Built using OpenStreetMap Nominatim and Overpass APIs.