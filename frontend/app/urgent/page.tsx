import { Suspense } from "react";
import UrgentPreview from "@/components/UrgentPreview";

// Preview route for design review. The real app renders <UrgentCard /> from the check-in flow.
export default function UrgentPage() {
  return (
    <Suspense fallback={null}>
      <UrgentPreview />
    </Suspense>
  );
}
