// Minimal, dependency-free Markdown renderer for assistant messages.
//
// Covers what the models actually emit: headings, bold/italic, inline code,
// fenced code blocks, bullet/numbered lists, links, and paragraphs. Builds real
// React nodes (no dangerouslySetInnerHTML), so it's XSS-safe. If we later need
// tables/nested lists, swap this for react-markdown — the call site won't change.
import { Fragment, type ReactNode } from "react";

/** Inline formatting: **bold**, *italic*, `code`, [text](url). */
function renderInline(text: string, keyBase: string): ReactNode[] {
  const tokens: ReactNode[] = [];
  // Order matters: code first (so ** inside code isn't parsed), then links, bold, italic.
  const pattern = /(`[^`]+`)|(\[[^\]]+\]\([^)]+\))|(\*\*[^*]+\*\*)|(\*[^*]+\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) tokens.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyBase}-${i++}`;
    if (tok.startsWith("`")) {
      tokens.push(<code key={key} className="md-code">{tok.slice(1, -1)}</code>);
    } else if (tok.startsWith("[")) {
      const mm = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok)!;
      tokens.push(
        <a key={key} href={mm[2]} target="_blank" rel="noreferrer" className="md-link">
          {mm[1]}
        </a>,
      );
    } else if (tok.startsWith("**")) {
      tokens.push(<strong key={key}>{tok.slice(2, -2)}</strong>);
    } else {
      tokens.push(<em key={key}>{tok.slice(1, -1)}</em>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) tokens.push(text.slice(last));
  return tokens;
}

export function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.trim().startsWith("```")) {
      const body: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        body.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      blocks.push(
        <pre key={key++} className="md-pre">
          <code>{body.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    // Heading
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const level = h[1].length;
      const Tag = (`h${Math.min(level + 2, 6)}`) as keyof JSX.IntrinsicElements;
      blocks.push(
        <Tag key={key++} className="md-h">
          {renderInline(h[2], `h${key}`)}
        </Tag>,
      );
      i++;
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      blocks.push(
        <ul key={key++} className="md-ul">
          {items.map((it, n) => (
            <li key={n}>{renderInline(it, `ul${key}-${n}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      blocks.push(
        <ol key={key++} className="md-ol">
          {items.map((it, n) => (
            <li key={n}>{renderInline(it, `ol${key}-${n}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Blank line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph (gather consecutive non-empty, non-special lines)
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].trim().startsWith("```") &&
      !/^(#{1,4})\s+/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i]);
      i++;
    }
    blocks.push(
      <p key={key++} className="md-p">
        {para.map((pl, n) => (
          <Fragment key={n}>
            {n > 0 && <br />}
            {renderInline(pl, `p${key}-${n}`)}
          </Fragment>
        ))}
      </p>,
    );
  }

  return <div className="md">{blocks}</div>;
}
