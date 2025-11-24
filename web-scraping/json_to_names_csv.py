#!/usr/bin/env python3
"""Extract fields from a JSON file and write them to CSV or XLSX.

Usage examples:
  python .\web-scraping\json_to_names_csv.py -i cambridge.json -o names.csv
  python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o names_addresses.csv --fields name,address
  python .\web-scraping\json_to_names_csv.py -i .\nearby-institute.json -o nearby-names.xlsx --xlsx --fields name,address
"""
import argparse
import csv
import json
from typing import Any, Dict, List


def extract_name(item: Dict[str, Any]) -> str:
    # Prefer top-level 'name', fall back to 'tags.name' or empty string
    name = item.get("name")
    if name:
        return name
    tags = item.get("tags") or {}
    return tags.get("name", "")


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # If top-level is a dict with a list under 'results' or similar, try to find list
    if isinstance(data, dict):
        # common keys that may contain the list
        for key in ("results", "elements", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # otherwise assume the dict itself represents a single item
        return [data]
    if isinstance(data, list):
        return data
    return []


def write_csv(names: List[str], out_path: str, encoding: str = "utf-8-sig") -> None:
    """Write CSV using the specified encoding.

    Default encoding is `utf-8-sig` which writes a BOM so Excel on Windows
    recognizes UTF-8 and displays Bangla correctly.
    This function is kept for backward compatibility (single-column name output).
    """
    with open(out_path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(["name"])  # header
        for n in names:
            writer.writerow([n])


def write_rows_csv(rows: List[List[str]], headers: List[str], out_path: str, encoding: str = "utf-8-sig") -> None:
    """Write rows (list of lists) to CSV with headers."""
    with open(out_path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)


def write_xlsx(names: List[str], out_path: str) -> None:
    """Write names to an Excel .xlsx file using openpyxl.

    If `openpyxl` is not installed, instruct the user to install it.
    """
    try:
        from openpyxl import Workbook
    except Exception:
        raise RuntimeError(
            "Writing .xlsx requires openpyxl. Install with: pip install openpyxl"
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Names"
    ws.append(["name"])  # header
    for n in names:
        ws.append([n])
    wb.save(out_path)


def write_rows_xlsx(rows: List[List[str]], headers: List[str], out_path: str) -> None:
    try:
        from openpyxl import Workbook
    except Exception:
        raise RuntimeError(
            "Writing .xlsx requires openpyxl. Install with: pip install openpyxl"
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(out_path)


def extract_address(tags: Dict) -> str:
    parts = []
    for key in ("addr:housenumber", "addr:street", "addr:city", "addr:postcode", "addr:country"):
        v = tags.get(key)
        if v:
            parts.append(v)
    if parts:
        return ", ".join(parts)
    return tags.get("addr:full") or tags.get("contact:address") or ""


def extract_phone(tags: Dict) -> str:
    for key in ("phone", "contact:phone", "telephone"):
        if key in tags:
            return tags[key]
    return ""


def determine_category(item: Dict[str, Any]) -> str:
    """Determine whether an item is a 'school', 'college', 'madrasa', or 'other'.

    Heuristics used (in order):
    - Check explicit tags: amenity, building, office
    - Check common keywords in name or tags (case-insensitive), including Bangla keywords
    - Default to 'other'
    """
    tags = (item.get("tags") or {})
    amenity = (tags.get("amenity") or "").lower()
    building = (tags.get("building") or "").lower()
    office = (tags.get("office") or "").lower()
    name = (extract_name(item) or "").lower()

    # explicit tag checks
    if amenity in ("school",):
        return "school"
    if amenity in ("college", "university") or building in ("college", "university"):
        return "college"

    # madrasa detection: keyword in name or a tag
    madrasa_keywords = ["madrasa", "madrash", "মাদ্রাসা", "মাদ্রাসা"]
    for kw in madrasa_keywords:
        if kw in name:
            return "madrasa"
    # also check tags that may indicate religious school
    if tags.get("madrasa") or tags.get("religion") == "muslim" and "madrasa" in name:
        return "madrasa"

    # broader heuristics for schools vs colleges: name keywords
    school_keywords = ["school", "schooling", "বিদ্যালয়", "বিদ্যালয়", "primary", "secondary"]
    college_keywords = ["college", "university", "institute", "institute of", "কলেজ", "বিশ্ববিদ্যালয়"]
    for kw in school_keywords:
        if kw in name:
            return "school"
    for kw in college_keywords:
        if kw in name:
            return "college"

    # office/building tags indicating education
    if office in ("education", "training") or building in ("school",):
        return "school"

    return "other"


def extract_value(item: Dict[str, Any], field: str) -> str:
    tags = item.get("tags") or {}
    field = field.strip()
    if field == "name":
        return extract_name(item) or ""
    if field == "address":
        # Prefer top-level address, fall back to tags
        return (item.get("address") or extract_address(tags) or "")
    if field == "phone":
        return (item.get("phone") or extract_phone(tags) or "")
    if field == "category":
        return determine_category(item)
    if field in ("lat", "lon", "osm_id", "osm_type"):
        return str(item.get(field, "")) if item.get(field, None) is not None else ""
    # generic: top-level then tags
    return str(item.get(field) or tags.get(field) or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract fields from JSON to CSV or XLSX")
    parser.add_argument("-i", "--input", required=True, help="Input JSON file path")
    parser.add_argument("-o", "--output", required=True, help="Output file path (CSV or XLSX)")
    parser.add_argument("--xlsx", action="store_true", help="Write an Excel .xlsx file instead of CSV (requires openpyxl)")
    parser.add_argument("--fields", default="name", help="Comma-separated fields to extract (default: name). E.g. --fields name,address,phone")
    args = parser.parse_args()

    items = load_json(args.input)
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    rows: List[List[str]] = []
    for it in items:
        row = [extract_value(it, f) for f in fields]
        # include even if some fields are empty; drop entirely empty rows
        if any(cell for cell in row):
            rows.append(row)

    out_lower = args.output.lower()
    try:
        if args.xlsx or out_lower.endswith(".xlsx"):
            write_rows_xlsx(rows, fields, args.output)
        else:
            write_rows_csv(rows, fields, args.output, encoding="utf-8-sig")
    except RuntimeError as e:
        print(str(e))
        return

    print(f"Wrote {len(rows)} rows with fields {fields} to {args.output}")


if __name__ == "__main__":
    main()
