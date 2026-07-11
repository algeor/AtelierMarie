/**
 * Validates a redirect path to prevent open redirect attacks.
 * Returns the path if valid (starts with `/` and not `//`),
 * otherwise returns `/`.
 */
export function validateRedirectPath(path: string): string {
  if (path.startsWith("/") && !path.startsWith("//")) {
    return path;
  }
  return "/";
}
