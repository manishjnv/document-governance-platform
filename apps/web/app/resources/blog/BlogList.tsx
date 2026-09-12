'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PILLAR_LABELS, type BlogPost, type Pillar } from './data';

type Filter = Pillar | 'all';

const CHIPS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All posts' },
  ...(Object.keys(PILLAR_LABELS) as Pillar[]).map((k) => ({ key: k, label: PILLAR_LABELS[k] })),
];

/** Pillar filter chips + post list. Native buttons with aria-pressed, so
 * keyboard users get Tab/Enter/Space for free. */
export function BlogList({ posts }: { posts: BlogPost[] }) {
  const [filter, setFilter] = useState<Filter>('all');
  const visible = filter === 'all' ? posts : posts.filter((p) => p.pillar === filter);

  return (
    <>
      <div role="group" aria-label="Filter posts by product" className="flex flex-wrap gap-2 mb-8">
        {CHIPS.map((c) => {
          const active = filter === c.key;
          return (
            <button
              key={c.key}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(c.key)}
              className={`rounded-full border px-3 py-1 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                active ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-muted'
              }`}
            >
              {c.label}
            </button>
          );
        })}
      </div>

      <ul className="space-y-6" aria-live="polite">
        {visible.map((post) => (
          <li key={post.slug} className="rounded-lg border p-5">
            <h2 className="font-semibold mb-1">
              <Link href={`/resources/blog/${post.slug}`} className="hover:underline">
                {post.title}
              </Link>
            </h2>
            <p className="text-sm text-muted-foreground mb-2">{post.dek}</p>
            <p className="text-xs text-muted-foreground">
              {new Date(post.publishedDate).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}{' '}
              &middot; By {post.author}
              {post.pillar ? <> &middot; {PILLAR_LABELS[post.pillar]}</> : null}
            </p>
          </li>
        ))}
        {visible.length === 0 && (
          <li className="text-sm text-muted-foreground">No posts in this category yet.</li>
        )}
      </ul>
    </>
  );
}
