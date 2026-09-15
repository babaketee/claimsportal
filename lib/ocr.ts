import "server-only";
import path from "node:path";
import fs from "node:fs";
import { createWorker } from "tesseract.js";

// ---------------------------------------------------------------------------
// OCR for uploaded claim documents.
//
// Images (jpg/png/webp) are OCR'd with tesseract.js, using the English
// traineddata bundled locally via the @tesseract.js-data/eng npm package —
// this avoids tesseract.js's default behaviour of fetching the ~13MB
// language file from a CDN on every cold start, which is both slow and
// often blocked by locked-down network policies.
//
// Text-based PDFs (i.e. not scanned images) have their embedded text
// extracted directly via pdf-parse, which is faster and more accurate than
// rasterising + OCR'ing a page that already contains real text.
// ---------------------------------------------------------------------------

const IMAGE_MIME_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"]);

const TESS_CACHE_DIR = path.join(process.cwd(), "data", "tess-cache");

function tessLangPath(): string {
  // Deliberately not require.resolve()'d: under Next.js's webpack bundling,
  // require.resolve on a non-code data package can return a bundler module
  // id instead of a real filesystem path. A path built from process.cwd()
  // is robust in both the Next server bundle and plain tsx/node execution.
  return path.join(process.cwd(), "node_modules", "@tesseract.js-data", "eng", "4.0.0_best_int");
}

export interface OcrResult {
  status: "done" | "unsupported" | "failed";
  text: string | null;
  error?: string;
}

export async function runOcr(filePath: string, mimeType: string): Promise<OcrResult> {
  try {
    if (IMAGE_MIME_TYPES.has(mimeType)) {
      if (!fs.existsSync(TESS_CACHE_DIR)) fs.mkdirSync(TESS_CACHE_DIR, { recursive: true });
      const worker = await createWorker("eng", 1, {
        langPath: tessLangPath(),
        cachePath: TESS_CACHE_DIR,
        gzip: true,
        logger: () => {},
      });
      try {
        const {
          data: { text },
        } = await worker.recognize(filePath);
        return { status: "done", text: text.trim() };
      } finally {
        await worker.terminate();
      }
    }

    if (mimeType === "application/pdf") {
      // pdf-parse only recovers text that already exists in the PDF (digital
      // documents / exports). A scanned image-only PDF has no embedded text
      // layer, so it comes back empty — that's a real limitation of this
      // demo pipeline, not a bug, and is surfaced to the reviewer as such.
      const { PDFParse } = await import("pdf-parse");
      const buf = fs.readFileSync(filePath);
      const parser = new PDFParse({ data: buf });
      const result = await parser.getText();
      await parser.destroy().catch(() => {});
      const text = (result.text || "").trim();
      if (!text) {
        return {
          status: "unsupported",
          text: null,
          error: "No embedded text layer found (likely a scanned image PDF — image-only OCR for PDFs is not enabled in this demo).",
        };
      }
      return { status: "done", text };
    }

    return { status: "unsupported", text: null, error: `OCR not supported for MIME type ${mimeType}.` };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[ocr] runOcr failed:", err);
    return {
      status: "failed",
      text: null,
      error: err instanceof Error ? err.message : "Unknown OCR error.",
    };
  }
}
