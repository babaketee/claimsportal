"""document_store.py — File ops, GPS EXIF extraction, MIME validation"""
"""Phase 1: local FS storage. Production: S3/GCS."""

import os, uuid, io
from datetime import datetime, timezone

ALLOWED_EXTENSIONS = {".pdf",".png",".jpg",".jpeg",".docx",".xlsx",".txt"}
ALLOWED_MIME_TYPES = {"application/pdf","image/png","image/jpeg","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","text/plain"}
DATA_DIR = "data/documents"

def get_storage_path(claim_ref: str, doc_id: str, filename: str) -> str:
    path = os.path.join(DATA_DIR, claim_ref, doc_id)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)

def validate_file(file_name: str, mime_type: str) -> tuple[bool, str]:
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension {ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}"
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type {mime_type} not allowed."
    return True, "OK"

def extract_gps_from_exif(file_bytes: bytes) -> dict | None:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        img = Image.open(io.BytesIO(file_bytes))
        exif = img._getexif()
        if not exif: return None
        gps_ifd = {}
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for k, v in value.items():
                    gps_ifd[GPSTAGS.get(k, k)] = v
        if not gps_ifd: return None
        def conv(data, ref):
            d, m, s = data
            r = d + m/60 + s/3600
            return -r if ref in ["S","W"] else r
        lat = conv(gps_ifd["GPSLatitude"], gps_ifd["GPSLatitudeRef"]) if "GPSLatitude" in gps_ifd else None
        lon = conv(gps_ifd["GPSLongitude"], gps_ifd["GPSLongitudeRef"]) if "GPSLongitude" in gps_ifd else None
        alt = gps_ifd.get("GPSAltitude")
        ts  = gps_ifd.get("GPSTimeStamp")
        return {"lat": lat, "lon": lon, "altitude": alt, "timestamp": str(ts)} if lat is not None else None
    except Exception:
        return None

def save_file(claim_ref: str, file_name: str, file_bytes: bytes, gps_metadata: dict | None) -> tuple[str, str]:
    doc_id = str(uuid.uuid4())
    stored_name = f"{doc_id}_{file_name}"
    path = get_storage_path(claim_ref, doc_id, stored_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return doc_id, stored_name

def trigger_virus_scan(doc_id: str) -> None:
    pass  # Phase 1: stub — ClamAV integration in Phase 2
