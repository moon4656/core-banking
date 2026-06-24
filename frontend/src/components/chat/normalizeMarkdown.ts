export function normalizeMarkdown(content: string) {
  const lines = content
    .replace(/\r\n/g, "\n")
    .replace(/\n{2,}(?=\s*([-*]|\d+\.)\s)/g, "\n")
    .split("\n");
  const normalized: string[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const current = lines[index].trim();
    const next = lines[index + 1]?.trimStart() ?? "";

    if (/^([*-]|\d+\.)\s*$/.test(current) && next) {
      normalized.push(`${current} ${next}`);
      index += 1;
      continue;
    }

    const headingMatch = current.match(/^([*-]|\d+\.)\s+\*\*(.+?)\*\*$/);
    if (headingMatch) {
      normalized.push(`### ${headingMatch[2]}`);
      continue;
    }

    const numberedSectionMatch = current.match(/^\d+\.\s+(.+?)(?::)?$/);
    if (numberedSectionMatch && /^[-*]\s/.test(next)) {
      normalized.push(`#### ${numberedSectionMatch[1]}`);
      continue;
    }

    const standaloneSectionMatch =
      current &&
      !/^([*-]|\d+\.)\s/.test(current) &&
      !/^#{1,6}\s/.test(current) &&
      next &&
      (/^([*-]|\d+\.)\s/.test(next) || /:$/.test(current));
    if (standaloneSectionMatch) {
      normalized.push(`#### ${current.replace(/:$/, "")}`);
      continue;
    }

    normalized.push(current);
  }

  return normalized
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
