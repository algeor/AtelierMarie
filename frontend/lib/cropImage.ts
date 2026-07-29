/**
 * Canvas helper for react-easy-crop: renders the cropped (and optionally
 * rotated) region of an image to a JPEG File. Adapted from the react-easy-crop
 * documentation example. The output is a fresh JPEG with no EXIF metadata; the
 * backend applies its own orientation/quality processing on upload.
 */

export interface PixelCrop {
  x: number;
  y: number;
  width: number;
  height: number;
}

function createImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new window.Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", (error) => reject(error));
    image.src = url;
  });
}

function toRadian(degree: number): number {
  return (degree * Math.PI) / 180;
}

/** Bounding box of an image after rotation, so nothing is clipped. */
function rotateSize(
  width: number,
  height: number,
  rotation: number
): { width: number; height: number } {
  const rotRad = toRadian(rotation);
  return {
    width: Math.abs(Math.cos(rotRad) * width) + Math.abs(Math.sin(rotRad) * height),
    height: Math.abs(Math.sin(rotRad) * width) + Math.abs(Math.cos(rotRad) * height),
  };
}

/**
 * Produce a cropped/rotated JPEG File from a source image URL and the crop
 * rectangle (in source pixels) reported by react-easy-crop.
 */
export async function getCroppedImg(
  imageSrc: string,
  pixelCrop: PixelCrop,
  rotation = 0,
  fileName = "product-image.jpg"
): Promise<File> {
  const image = await createImage(imageSrc);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not obtain a 2D canvas context");

  const rotRad = toRadian(rotation);
  const { width: bBoxWidth, height: bBoxHeight } = rotateSize(
    image.width,
    image.height,
    rotation
  );

  // Draw the rotated image onto a canvas sized to its rotated bounding box.
  canvas.width = bBoxWidth;
  canvas.height = bBoxHeight;
  ctx.translate(bBoxWidth / 2, bBoxHeight / 2);
  ctx.rotate(rotRad);
  ctx.translate(-image.width / 2, -image.height / 2);
  ctx.drawImage(image, 0, 0);

  // Extract just the crop rectangle, then resize the canvas down to it.
  const cropped = ctx.getImageData(
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height
  );
  canvas.width = pixelCrop.width;
  canvas.height = pixelCrop.height;
  ctx.putImageData(cropped, 0, 0);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Canvas export produced an empty blob"));
          return;
        }
        resolve(new File([blob], fileName, { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.95
    );
  });
}
