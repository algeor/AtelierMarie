"use client";

import { useAuth } from "@/contexts/AuthContext";
import { ReactionBar } from "./ReactionBar";
import { CommentThread } from "./CommentThread";

interface ProductSocialSectionProps {
  productId: string;
}

/**
 * Client boundary for social features (reactions + comments).
 * Reads auth state to determine if the user is logged in with a name.
 */
export function ProductSocialSection({ productId }: ProductSocialSectionProps) {
  const { user } = useAuth();
  const isLoggedInWithName = Boolean(user?.name);

  return (
    <div className="space-y-8">
      <ReactionBar productId={productId} />
      <CommentThread
        productId={productId}
        isLoggedInWithName={isLoggedInWithName}
      />
    </div>
  );
}
