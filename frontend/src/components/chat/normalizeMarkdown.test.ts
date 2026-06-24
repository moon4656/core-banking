import assert from "node:assert/strict";

import { normalizeMarkdown } from "./normalizeMarkdown";

const source = `대출 신청 시 유의사항을 요약해 드리겠습니다.

1. 신용대출 심사 기준:
- 신용점수 650점 이상
- 연소득 3천만원 이상

2. 주택담보대출 LTV/DTI/DSR 기준:
- LTV: 투기지역 40%, 규제지역 60%, 일반지역 70%
- DTI: 60%
`;

const normalized = normalizeMarkdown(source);

assert.match(normalized, /#### 신용대출 심사 기준/);
assert.match(normalized, /#### 주택담보대출 LTV\/DTI\/DSR 기준/);
assert.doesNotMatch(normalized, /\n1\. 신용대출 심사 기준:/);
assert.doesNotMatch(normalized, /\n2\. 주택담보대출 LTV\/DTI\/DSR 기준:/);

console.log("normalizeMarkdown regression test passed");
