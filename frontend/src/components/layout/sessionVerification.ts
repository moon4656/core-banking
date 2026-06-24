import { AuthSessionResponse } from "@/lib/api";

let verifiedSession: AuthSessionResponse | null = null;
let verifySessionPromise: Promise<AuthSessionResponse> | null = null;

export function primeVerifiedSession(session: AuthSessionResponse) {
  verifiedSession = session;
  verifySessionPromise = Promise.resolve(session);
}

export function resetVerifiedSession() {
  verifiedSession = null;
  verifySessionPromise = null;
}

export function hasVerifiedSession() {
  return verifiedSession !== null;
}

export async function getVerifiedSession(
  fetcher: () => Promise<AuthSessionResponse>
) {
  if (verifiedSession) {
    return verifiedSession;
  }

  if (!verifySessionPromise) {
    verifySessionPromise = fetcher()
      .then((profile) => {
        verifiedSession = profile;
        return profile;
      })
      .catch((error) => {
        resetVerifiedSession();
        throw error;
      });
  }

  return verifySessionPromise;
}
