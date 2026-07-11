import { Suspense } from "react";
import { CallbackHandler } from "./CallbackHandler";

function LoadingSpinner() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-soft-brown border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-soft-brown font-medium">Signing you in...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <CallbackHandler />
    </Suspense>
  );
}
