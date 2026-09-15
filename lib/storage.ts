import "server-only";
import fs from "node:fs";
import path from "node:path";

// ---------------------------------------------------------------------------
// Local disk storage for uploaded claim documents. Files live under
// data/uploads/<claim_ref>/ so they sit alongside the SQLite database and
// are easy to back up or swap for S3/Azure Blob in a real deployment.
// ---------------------------------------------------------------------------

const UPLOAD_ROOT = path.join(process.cwd(), "data", "uploads");

export function uploadDirFor(claim_ref: string): string {
  const dir = path.join(UPLOAD_ROOT, claim_ref.replace(/[^a-zA-Z0-9_-]/g, "_"));
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9_.-]/g, "_").slice(-120);
}

/** Persists an uploaded File/Blob to disk and returns its absolute path + size. */
export async function saveUploadedFile(
  claim_ref: string,
  doc_id: string,
  file: File
): Promise<{ filePath: string; fileSize: number }> {
  const dir = uploadDirFor(claim_ref);
  const filename = `${doc_id}-${safeFilename(file.name || "upload")}`;
  const filePath = path.join(dir, filename);
  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  fs.writeFileSync(filePath, buffer);
  return { filePath, fileSize: buffer.length };
}
