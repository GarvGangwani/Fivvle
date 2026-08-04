/** Client-side image resize before chat attachment upload. */

const MAX_IMAGE_EDGE_PX = 1500;
const JPEG_QUALITY = 0.85;

function isRasterImageFile(file: File): boolean {
  const mime = file.type.toLowerCase();
  if (mime === "image/png" || mime === "image/jpeg" || mime === "image/webp") {
    return true;
  }
  const name = file.name.toLowerCase();
  return (
    name.endsWith(".png") ||
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".webp")
  );
}

function outputMime(file: File): "image/jpeg" | "image/png" | "image/webp" {
  const mime = file.type.toLowerCase();
  if (mime === "image/png") return "image/png";
  if (mime === "image/webp") return "image/webp";
  return "image/jpeg";
}

/**
 * Cap the longest edge at ~1500px and re-encode. Skips when already small.
 * Keeps aspect ratio. Falls back to the original file on any failure.
 */
export async function downscaleImageForUpload(file: File): Promise<File> {
  if (!isRasterImageFile(file)) return file;
  if (typeof createImageBitmap !== "function") return file;

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return file;
  }

  try {
    const longest = Math.max(bitmap.width, bitmap.height);
    if (longest <= MAX_IMAGE_EDGE_PX) {
      return file;
    }

    const scale = MAX_IMAGE_EDGE_PX / longest;
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;

    ctx.drawImage(bitmap, 0, 0, width, height);

    const mime = outputMime(file);
    const blob = await new Promise<Blob | null>((resolve) => {
      if (mime === "image/jpeg") {
        canvas.toBlob(resolve, mime, JPEG_QUALITY);
      } else {
        canvas.toBlob(resolve, mime);
      }
    });
    if (!blob || blob.size === 0) return file;

    // Prefer smaller payload; if re-encode grew (rare for PNG), keep original.
    if (blob.size >= file.size) return file;

    return new File([blob], file.name, {
      type: mime,
      lastModified: Date.now(),
    });
  } catch {
    return file;
  } finally {
    bitmap.close();
  }
}
