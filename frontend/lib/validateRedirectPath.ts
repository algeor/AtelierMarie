/**
 * Validates a redirect path to prevent open redirect vulnerabilities.
 * Returns the path if it starts with "/" and does NOT start with "//"
 * (rejects absolute URLs and protocol-relative URLs).
 * Also rejects backslashes (browser normalization to //), control characters,
 * path traversal segments (..), and strips query strings/fragments.
 * Returns "/" as a safe fallback for all invalid paths.
 */
export function validateRedirectPath(path: string): string {
  if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//")) {
    return "/";
  }
  // Strip query string and fragment — only the pathname matters for redirect
  const cleanPath = path.split(/[?#]/)[0]!;
  // Reject backslashes, control chars, and path traversal
  if (
    cleanPath.includes("\\") ||
    /[\x00-\x1f]/.test(cleanPath) ||
    cleanPath.split("/").some((segment) => segment === ".." || segment === ".")
  ) {
    return "/";
  }
  return cleanPath;
}
