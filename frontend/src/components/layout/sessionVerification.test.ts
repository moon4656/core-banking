import assert from "node:assert/strict";

import {
  getVerifiedSession,
  hasVerifiedSession,
  primeVerifiedSession,
  resetVerifiedSession,
} from "./sessionVerification.js";

resetVerifiedSession();

let fetchCount = 0;
const first = await getVerifiedSession(async () => {
  fetchCount += 1;
  return {
    name: "portal-user",
    role: "ANALYST",
    auth_mode: "api-key",
    access_token: "token-1",
    token_type: "Bearer",
  };
});
const second = await getVerifiedSession(async () => {
  fetchCount += 1;
  return {
    name: "other",
    role: "ADMIN",
    auth_mode: "api-key",
    access_token: "token-2",
    token_type: "Bearer",
  };
});

assert.equal(fetchCount, 1);
assert.equal(first.access_token, "token-1");
assert.equal(second.access_token, "token-1");
assert.equal(hasVerifiedSession(), true);

resetVerifiedSession();
primeVerifiedSession({
  name: "primed",
  role: "ADMIN",
  auth_mode: "api-key",
  access_token: "token-3",
  token_type: "Bearer",
});

const third = await getVerifiedSession(async () => {
  throw new Error("should not fetch after prime");
});

assert.equal(third.access_token, "token-3");

resetVerifiedSession();
assert.equal(hasVerifiedSession(), false);

console.log("sessionVerification regression test passed");
