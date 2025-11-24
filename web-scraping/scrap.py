"""Near-by institutes scraper using OpenStreetMap Overpass API.

Usage:
  - Provide a `--location` string (e.g. "Seattle, WA") to geocode via Nominatim,
	or omit it to fall back to IP-based geolocation.
  - Adjust `--radius` in meters (default 2000m).
  - Save results with `--output` (CSV or JSON determined by `--format`).

Notes:
  - This uses public Nominatim and Overpass APIs. Respect their usage policies
	and avoid-heavy automated scraping. Add delays or use your own instance
	for large volume.
"""

import argparse
import csv
import json
import os
import requests
from typing import Tuple, List, Dict, Optional

# Prefer a contact email for Nominatim per usage policy. Set via env var `OSM_EMAIL`.
OSM_EMAIL = os.getenv("OSM_EMAIL")
default_user_agent = "NearbyInstitutesScraper/1.0"
if OSM_EMAIL:
	HEADERS = {"User-Agent": f"{default_user_agent} ({OSM_EMAIL})"}
else:
	HEADERS = {"User-Agent": f"{default_user_agent} (+https://example.com)"}


def geocode_location(location: Optional[str]) -> Tuple[float, float]:
	"""Return (lat, lon). If `location` is None, fall back to IP-based geolocation."""
	if location:
		url = "https://nominatim.openstreetmap.org/search"
		params = {"q": location, "format": "json", "limit": 1}
		# include email if available (recommended by Nominatim)
		if OSM_EMAIL:
			params["email"] = OSM_EMAIL
		try:
			resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
			resp.raise_for_status()
		except requests.exceptions.HTTPError as e:
			# Provide a helpful hint for 403 Forbidden from Nominatim
			if getattr(e.response, "status_code", None) == 403:
				raise RuntimeError(
					"Nominatim returned 403 Forbidden.\n"
					"This often occurs when the request lacks a proper User-Agent or contact email.\n"
					"Set the environment variable `OSM_EMAIL` to your contact email and retry, e.g.:\n"
					"  $env:OSM_EMAIL='you@example.com'; python .\\web-scraping\\scrap.py -l \"Shonir Akhra\" -r 3000 -o res.csv\n"
				) from e
			raise
		data = resp.json()
		if not data:
			raise ValueError(f"Location not found via Nominatim: {location}")
		lat = float(data[0]["lat"])
		lon = float(data[0]["lon"])
		return lat, lon

	# fallback: IP-based lookup
	resp = requests.get("https://ipinfo.io/json", headers=HEADERS, timeout=10)
	resp.raise_for_status()
	data = resp.json()
	lat_str, lon_str = data.get("loc", "0,0").split(",")
	return float(lat_str), float(lon_str)


def build_overpass_query(lat: float, lon: float, radius: int, mode: str = "strict") -> str:
	"""Build Overpass query. In `strict` mode, only request known institute tags.
	In `loose` mode, include broader heuristics (name keywords, building/office heuristics).
	"""
	q = f"[out:json][timeout:45];("
	if mode == "strict":
		# Request only common, explicit institute tags to reduce false positives
		amenities = "school|college|university|kindergarten|library|research"
		building_vals = "school|college|university"
		office_vals = "education|training"

		q += f"node[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"
		q += f"way[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"

		q += f"node[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"
		q += f"way[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"

		q += f"node[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"
		q += f"way[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"
	else:
		# loose: include name heuristics and broader tags (previous behavior)
		amenities = "school|college|university|kindergarten|training|research|library"
		building_vals = "school|college|university|training"
		office_vals = "education|training"
		name_keywords = "Institute|Academy|Center|Centre|Training|College|University|School"

		q += f"node[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"
		q += f"way[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"amenity\"~\"{amenities}\"](around:{radius},{lat},{lon});"

		q += f"node[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"
		q += f"way[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"building\"~\"{building_vals}\"](around:{radius},{lat},{lon});"

		q += f"node[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"
		q += f"way[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"office\"~\"{office_vals}\"](around:{radius},{lat},{lon});"

		q += f"node[\"name\"~\"{name_keywords}\"](around:{radius},{lat},{lon});"
		q += f"way[\"name\"~\"{name_keywords}\"](around:{radius},{lat},{lon});"
		q += f"relation[\"name\"~\"{name_keywords}\"](around:{radius},{lat},{lon});"

	q += ");out center tags;"
	return q


def query_overpass(lat: float, lon: float, radius: int) -> List[Dict]:
	url = "https://overpass-api.de/api/interpreter"
	query = build_overpass_query(lat, lon, radius)
	resp = requests.post(url, data=query.encode("utf-8"), headers=HEADERS, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	return data.get("elements", [])


def extract_address(tags: Dict) -> str:
	parts = []
	for key in ("addr:housenumber", "addr:street", "addr:city", "addr:postcode", "addr:country"):
		v = tags.get(key)
		if v:
			parts.append(v)
	if parts:
		return ", ".join(parts)
	# fallback to addr:full or 'contact:address'
	return tags.get("addr:full") or tags.get("contact:address") or ""


def extract_phone(tags: Dict) -> str:
	for key in ("phone", "contact:phone", "telephone"):
		if key in tags:
			return tags[key]
	return ""


def parse_elements(elements: List[Dict], mode: str = "strict") -> List[Dict]:
	results = []
	seen = set()
	for el in elements:
		# Deduplicate by element type+id to avoid duplicates from multiple queries
		el_id = (el.get("type"), el.get("id"))
		if el_id in seen:
			continue
		seen.add(el_id)

		tags = el.get("tags", {})
		name = tags.get("name")
		if not name:
			# skip unnamed objects (we only want named institutes)
			continue

		# In strict mode only accept objects with explicit institute tags
		if mode == "strict":
			amenity = tags.get("amenity", "").lower()
			building = tags.get("building", "").lower()
			office = tags.get("office", "").lower()
			allowed_amenities = {"school", "college", "university", "kindergarten", "library", "research"}
			allowed_buildings = {"school", "college", "university"}
			allowed_offices = {"education", "training"}

			if not (amenity in allowed_amenities or building in allowed_buildings or office in allowed_offices):
				# skip if it doesn't have explicit institute tags
				continue
		lat = el.get("lat") or (el.get("center") or {}).get("lat")
		lon = el.get("lon") or (el.get("center") or {}).get("lon")
		address = extract_address(tags)
		phone = extract_phone(tags)
		results.append({
			"osm_type": el.get("type"),
			"osm_id": el.get("id"),
			"name": name,
			"address": address,
			"phone": phone,
			"lat": lat,
			"lon": lon,
			"tags": tags,
		})
	return results


def save_results(results: List[Dict], output: str, fmt: str = "csv"):
	if fmt == "json" or output.lower().endswith(".json"):
		with open(output, "w", encoding="utf-8") as f:
			json.dump(results, f, ensure_ascii=False, indent=2)
		return

	# default CSV
	keys = ["name", "address", "phone", "lat", "lon"]
	with open(output, "w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=keys)
		writer.writeheader()
		for r in results:
			row = {k: r.get(k, "") for k in keys}
			writer.writerow(row)


# def main():
# 	parser = argparse.ArgumentParser(description="Find nearby institutes using OSM Overpass API")
# 	parser.add_argument("--location", "-l", help="Location string to geocode (e.g. 'Boston, MA')")
# 	parser.add_argument("--radius", "-r", type=int, default=2000, help="Radius in meters (default 2000)")
# 	parser.add_argument("--output", "-o", default="results.csv", help="Output file (CSV or JSON)")
# 	parser.add_argument("--format", "-f", choices=["csv", "json"], default=None, help="Output format (csv/json)")
# 	args = parser.parse_args()

# 	lat, lon = geocode_location(args.location)
# 	print(f"Using coordinates: {lat}, {lon}")

# 	elements = query_overpass(lat, lon, args.radius)
# 	print(f"Found {len(elements)} raw elements from Overpass")
# 	results = parse_elements(elements)
# 	print(f"Parsed {len(results)} institutes with names")

# 	outfmt = args.format or ("json" if args.output.lower().endswith(".json") else "csv")
# 	save_results(results, args.output, outfmt)
# 	print(f"Saved {len(results)} results to {args.output}")


# if __name__ == "__main__":
# 	main()
def main():
    parser = argparse.ArgumentParser(description="Find nearby institutes using OSM Overpass API")
    parser.add_argument("--location", "-l", help="Location string to geocode (e.g. 'Boston, MA')")
    parser.add_argument("--radius", "-r", type=int, default=2000, help="Radius in meters (default 2000)")
    parser.add_argument("--output", "-o", default="results.csv", help="Output file (CSV or JSON)")
    parser.add_argument("--format", "-f", choices=["csv", "json"], default=None, help="Output format (csv/json)")
    parser.add_argument("--lat", type=float, help="Explicit latitude coordinate.")
    parser.add_argument("--lon", type=float, help="Explicit longitude coordinate.")
    args = parser.parse_args()

    # --- Priority Logic for Coordinates ---
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
        print(f"Using explicit coordinates from command line: {lat}, {lon}")
    elif args.location is None and args.lat is None and args.lon is None:
        # **NEW: Use hardcoded coordinates if no arguments are provided**
        lat, lon = 23.6899938, 90.4256277
        print(f"Using default hardcoded coordinates (Dhaka): {lat}, {lon}")
    else:
        # Fallback to geocoding or IP lookup
        lat, lon = geocode_location(args.location)
        print(f"Using determined coordinates: {lat}, {lon}")
    # --------------------------------------

    elements = query_overpass(lat, lon, args.radius)
    print(f"Found {len(elements)} raw elements from Overpass")
    results = parse_elements(elements)
    print(f"Parsed {len(results)} institutes with names")

    outfmt = args.format or ("json" if args.output.lower().endswith(".json") else "csv")
    save_results(results, args.output, outfmt)
    print(f"Saved {len(results)} results to {args.output}")


if __name__ == "__main__":
    main()