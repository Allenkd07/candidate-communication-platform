import { Suspense } from "react";

import { CandidatesPage } from "@/features/candidates/CandidatesPage";

export default function HomePage() {
  // CandidatesPage reads useSearchParams, which needs a Suspense boundary to prerender.
  return (
    <Suspense>
      <CandidatesPage />
    </Suspense>
  );
}
