"""
Parse GLEIF golden copy ZIP files (full or delta) containing XML.

GLEIF distributes LEI-CDF v3.1 XML files inside a ZIP archive.
The XML uses a namespace like:
  {http://www.gleif.org/data/schema/leidata/2016}

We use iterparse to stream through the file one LEIRecord at a time,
so even the full 3M+ record file won't blow up RAM.
"""

import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Generator
from pathlib import Path

# Fields we extract from each LEIRecord, mapped to DB column names.
# Each value is a tuple of (parent_tag, child_tag) relative to the LEIRecord element.
FIELD_MAP = {
    "lei":                       ("", "LEI"),
    "legal_name":                ("Entity", "LegalName"),
    "jurisdiction":              ("Entity", "LegalJurisdiction"),
    "entity_status":             ("Entity", "EntityStatus"),
    "entity_category":           ("Entity", "EntityCategory"),
    "managing_lou":              ("Registration", "ManagingLOU"),
    "registration_status":       ("Registration", "RegistrationStatus"),
    "initial_registration_date": ("Registration", "InitialRegistrationDate"),
    "last_update_date":          ("Registration", "LastUpdateDate"),
    "next_renewal_date":         ("Registration", "NextRenewalDate"),
}

DATE_FIELDS = {"initial_registration_date", "last_update_date", "next_renewal_date"}


def _detect_namespace(xml_file) -> str:
    """Read just enough of the XML to extract the namespace URI."""
    for event, elem in ET.iterparse(xml_file, events=("start",)):
        tag = elem.tag
        if tag.startswith("{"):
            return tag[1: tag.index("}")]
        break
    return ""


def _extract_text(record_elem, ns: str, parent: str, child: str) -> str | None:
    """Pull text from a child element, stripping the time portion from dates."""
    if parent:
        path = f"{{{ns}}}{parent}/{{{ns}}}{child}"
    else:
        path = f"{{{ns}}}{child}"
    elem = record_elem.find(path)
    if elem is None or not elem.text:
        return None
    text = elem.text.strip()
    # GLEIF dates look like "2015-03-24T00:00:00Z" — keep only the date part
    if "T" in text:
        text = text[:10]
    return text or None


def stream_records(zip_path: Path) -> Generator[dict, None, None]:
    """
    Yield one dict per LEIRecord from the GLEIF ZIP, using streaming XML parsing.
    Memory usage stays flat regardless of file size.
    """
    with zipfile.ZipFile(zip_path) as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            raise ValueError(f"No XML file found inside {zip_path.name}")
        xml_name = xml_names[0]

        # First pass: detect namespace
        with zf.open(xml_name) as f:
            ns = _detect_namespace(f)

        record_tag = f"{{{ns}}}LEIRecord" if ns else "LEIRecord"

        # Second pass: stream records
        with zf.open(xml_name) as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag != record_tag:
                    continue

                row: dict[str, str | None] = {}
                for db_col, (parent, child) in FIELD_MAP.items():
                    row[db_col] = _extract_text(elem, ns, parent, child)

                yield row

                # Critical: free memory after processing each record
                elem.clear()
