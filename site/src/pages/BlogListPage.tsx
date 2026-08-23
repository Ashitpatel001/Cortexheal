import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Clock, BookOpen, ShieldAlert, Cpu } from "lucide-react";

export const BLOG_POSTS = [
  {
    slug: "deterministic-safety-imperative",
    title: "Why LLMs Should Never Make Safety Decisions About LLMs (The Deterministic Imperative)",
    excerpt: "Using an LLM judge to evaluate whether another LLM agent is stuck or burning budget introduces latency compounding, non-reproducible rulings, and failure cascade risks. Here is why deterministic control planes are mathematically mandatory.",
    date: "August 2026",
    readTime: "7 min read",
    author: "CortexHeal Systems Engineering",
    category: "Architecture & Systems Safety",
    icon: ShieldAlert
  },
  {
    slug: "sub-millisecond-circuit-breakers",
    title: "Real-Time Circuit Breakers: How CortexHeal Protects Agent Fleets at Scale",
    excerpt: "A deep dive into our concurrent ring buffer, 0.15ms in-process telemetry handover, zero-lock memory caches, and PostgreSQL connection pooling under 50+ parallel agent streams.",
    date: "August 2026",
    readTime: "9 min read",
    author: "CortexHeal Core Team",
    category: "Performance & Scaling",
    icon: Cpu
  }
];

export function BlogListPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-mono font-semibold">
          <BookOpen className="w-3.5 h-3.5" /> Engineering &amp; Architecture Essays
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight">
          CortexHeal Engineering Blog
        </h1>
        <p className="text-base sm:text-lg text-slate-600">
          In-depth technical analyses on deterministic AI safety, concurrency control planes, and agent fleet reliability.
        </p>
      </div>

      <div className="space-y-8">
        {BLOG_POSTS.map((post) => {
          const Icon = post.icon;
          return (
            <article
              key={post.slug}
              className="p-8 bg-white border border-slate-200 rounded-2xl shadow-xs hover:shadow-md hover:border-blue-300 transition-all group"
            >
              <div className="flex items-center gap-4 text-xs text-slate-500 font-mono mb-4">
                <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 font-semibold uppercase">
                  {post.category}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> {post.readTime}
                </span>
                <span>•</span>
                <span>{post.date}</span>
              </div>

              <h2 className="text-2xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors mb-3">
                <Link to={`/blog/${post.slug}`}>{post.title}</Link>
              </h2>

              <p className="text-sm text-slate-600 leading-relaxed mb-6">
                {post.excerpt}
              </p>

              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <span className="text-xs text-slate-400 font-medium">By {post.author}</span>
                <Link
                  to={`/blog/${post.slug}`}
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 group-hover:text-blue-700"
                >
                  Read Essay <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
