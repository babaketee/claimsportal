import "server-only";
import fs from "node:fs";
import exifr from "exifr";
import type { PhotoMetadata } from "./types";

// ---------------------------------------------------------------------------
// Photo metadata retrieval for uploaded accident/damage photos.
//
// The workflow design document calls out photograph capture date and
// location metadata as "among the strongest available indicators of a
// staged or recycled loss". This module extracts EXIF capture time and GPS
// coordinates from uploaded images and flags mismatches against the
// claimed loss date, which the fraud-scoring engine (lib/fraud.ts) then
// weighs as one signal among several.
// ---------------------------------------------------------------------------

const IMAGE_MIME_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/tiff"]);

export async function extractPhotoMetadata(
  filePath: string,
  mimeType: string,
  claimedLossDate: string | null
): Promise<PhotoMetadata | null> {
  if (!IMAGE_MIME_TYPES.has(mimeType)) return null;

  const flags: string[] = [];
  let captured_at: string | null = null;
  let gps_lat: number | null = null;
  let gps_lng: number | null = null;
  let camera_make: string | null = null;
  let camera_model: string | null = null;

  try {
    const buf = fs.readFileSync(filePath);
    const tags = await exifr.parse(buf, { gps: true, exif: true, tiff: true }).catch(() => null);
    if (tags) {
      const dt: Date | undefined = tags.DateTimeOriginal || tags.CreateDate || tags.ModifyDate;
      if (dt instanceof Date && !Number.isNaN(dt.getTime())) {
        captured_at = dt.toISOString();
      }
      if (typeof tags.latitude === "number" && typeof tags.longitude === "number") {
        gps_lat = tags.latitude;
        gps_lng = tags.longitude;
      }
      camera_make = tags.Make ?? null;
      camera_model = tags.Model ?? null;
    }
  } catch {
    // Fall through — treat as a photo with no readable metadata.
  }

  const has_gps = gps_lat !== null && gps_lng !== null;
  if (!captured_at) {
    flags.push("No capture-date metadata present in the photo (stripped, screenshotted, or a messaging-app re-compression).");
  }
  if (!has_gps) {
    flags.push("No GPS location metadata present in the photo.");
  }

  let days_from_loss: number | null = null;
  if (captured_at && claimedLossDate) {
    const capturedMs = new Date(captured_at).getTime();
    const lossMs = new Date(claimedLossDate).getTime();
    if (!Number.isNaN(capturedMs) && !Number.isNaN(lossMs)) {
      days_from_loss = Math.round((capturedMs - lossMs) / 86400000);
      if (Math.abs(days_from_loss) > 2) {
        flags.push(
          `Photo capture date is ${Math.abs(days_from_loss)} day(s) ${days_from_loss > 0 ? "after" : "before"} the claimed loss date — possible staged or recycled loss photo.`
        );
      }
    }
  }

  return { captured_at, gps_lat, gps_lng, camera_make, camera_model, has_gps, days_from_loss, flags };
}
