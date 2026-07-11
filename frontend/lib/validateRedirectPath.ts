/**
 * Validates a redirect path to prevent open redirect vulnerabilities.
 * Returns the path if it starts with "/" and does NOT start with "//"
 * (rejects absolute URLs and protocol-relative URLs).
 * Also rejects backslashes (browser normalization to //) and control characters.
 * Returns "/" as a safe fallback for all invalid paths.
 */
export function validateRedirectPath(path: string): string {
  if (
    typeof path === "string" &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("\\") &&
    !/[\x00-\x1f]/.test(path)
  ) {
    return path;
  }
  return "/";
}
