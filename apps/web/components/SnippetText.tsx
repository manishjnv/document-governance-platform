/**
 * Renders a Postgres ts_headline snippet: match markers (<b>…</b>) become
 * <mark> highlights, everything else stays plain auto-escaped text.
 *
 * Deliberately NOT dangerouslySetInnerHTML — snippet bodies come from
 * uploaded-document / user content and ts_headline does not escape them, so
 * raw HTML rendering would be a stored-XSS sink (RCA #20). Unbalanced
 * markers can at worst mis-bold a segment; they can never inject markup.
 */

import { Fragment } from 'react';

export function SnippetText({ snippet }: { snippet: string }) {
  const parts = snippet.split(/<\/?b>/);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="bg-transparent font-semibold text-foreground">
            {part}
          </mark>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        )
      )}
    </>
  );
}

/** Tag-stripped plain text (tooltips, CSV, aria labels). */
export function snippetPlainText(snippet: string): string {
  return snippet.replace(/<\/?b>/g, '');
}
