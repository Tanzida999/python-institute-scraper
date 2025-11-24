# Nearby Institutes Scraper

A small Python toolset that finds nearby institutes (schools, colleges, universities, training centers, libraries) using OpenStreetMap's Nominatim (geocoding) and Overpass APIs, then lets you extract and export selected fields (name, address, phone, coordinates, category) to CSV or XLSX.

**Requirements**

- Python 3.8+
- `requests` library
- Optional for Excel output: `openpyxl`

Install dependencies:

```powershell
pip install requests
pip install openpyxl    # optional, only needed for .xlsx output
```

**Files**

- `web-scraping/scrap.py` — main scraper (queries Nominatim + Overpass)
- `web-scraping/json_to_names_csv.py` — utility to extract fields from a scraper JSON result and write CSV or XLSX

**Common scraper usage** (run from repository root; PowerShell):

```powershell
# Geocode 'Cambridge, MA' and save CSV
python .\web-scraping\scrap.py --location "Cambridge, MA" --radius 3000 --output results.csv

# Save JSON instead
python .\web-scraping\scrap.py -l "Cambridge, MA" -r 3000 -o results.json -f json

# Use IP-based location fallback (no --location) and default radius (2000m)
python .\web-scraping\scrap.py -r 2000 -o near_me.json -f json

# If Nominatim returns 403, set a contact email (recommended)
$env:OSM_EMAIL='you@example.com'; python .\web-scraping\scrap.py -l "Shonir Akhra" -r 3000 -o res.csv
```

**Extracting fields from the JSON output**

The `json_to_names_csv.py` utility reads the JSON file produced by the scraper (or any similar array/object) and writes a CSV or XLSX with selected fields.

Basic examples (PowerShell):

```powershell
# Extract only names to CSV (UTF-8 with BOM so Excel displays Bangla correctly)
python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o nearby-names.csv

# Extract name and address columns
python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o nearby-name-address.csv --fields name,address

# Extract name and auto-detected category (school/college/madrasa/other)
python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o nearby-name-category.csv --fields name,category

# Write a real Excel .xlsx (requires openpyxl)
pip install openpyxl
python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o nearby-name-address-category.xlsx --fields name,address,category --xlsx

# The utility will also infer output format from the output filename (.csv or .xlsx)
```

Supported fields (examples): `name`, `address`, `phone`, `lat`, `lon`, `osm_id`, `osm_type`, `category`.

- `category` is inferred by heuristics from OSM tags and name keywords (returns `school`, `college`, `madrasa`, or `other`).

**Excel / Bangla support**

- CSV files are written as UTF-8 with a BOM (`utf-8-sig`) so Excel on Windows correctly recognizes UTF-8 and displays Bangla text. If Excel still shows garbled text, use Data → From Text/CSV and choose UTF-8 as the file origin.
- For native `.xlsx` files, install `openpyxl` as shown above.

**Notes & Limitations**

- The scraper uses public Nominatim and Overpass endpoints — respect their usage policies and avoid heavy automated scraping. For heavy use, run your own instances or use paid APIs.
- OSM tagging is inconsistent; some objects may lack addresses, phones, or explicit tags for institute type. The `category` field is heuristic and may not be perfect.

If you want, I can:

- Add a `requirements.txt` with pinned versions.
- Run the extractor on `nearby-institute.json` and add the generated CSV/XLSX to the repository.
- Improve `category` heuristics for local language keywords you care about.

**Credits**

Built using OpenStreetMap Nominatim and Overpass APIs.