# Live Public Demo Setup Guide

This guide explains how to set up the **CortexHeal Live Demo** on your public-facing marketing site.

Because CortexHeal provides an interactive dashboard powered by a real-time SSE (Server-Sent Events) stream, you can embed it directly into your marketing site. Potential customers can watch autonomous agents getting caught and safely recovered *live*, without signing up or touching a terminal.

## 1. Hosting Requirements

To run this in production, you must provision actual internet-accessible infrastructure. **Local execution cannot bind to a public domain.**

You will need:
1. A **PostgreSQL database** (e.g., AWS RDS, Supabase, or Railway).
2. A **Python hosting environment** for the backend API (e.g., Render, Fly.io, or Heroku).
3. A **Static hosting provider** for the React frontend (e.g., Vercel, Netlify).

## 2. Generate a Viewer Token

For the public demo, you must use a heavily restricted `VIEWER` token. This token ensures visitors can view the incident queue and timeline but cannot approve recovery plans or manage API keys.

1. Log into your production CortexHeal dashboard as an `ADMIN`.
2. Navigate to **API Keys** in the sidebar.
3. Create a new key named `Marketing Site Embed` with the role **VIEWER**.
4. Copy the raw key (e.g., `ctx_viewer_9a8b7c6d...`).

## 3. Embed the iframe

On your marketing site (HTML, Webflow, Next.js, etc.), embed the following snippet. Replace `YOUR_FRONTEND_URL` with where you deployed the React app, and `YOUR_VIEWER_TOKEN` with the token generated above.

```html
<div class="cortexheal-demo-container" style="width: 100%; height: 800px; border-radius: 12px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
  <iframe 
    src="https://YOUR_FRONTEND_URL.com/?token=YOUR_VIEWER_TOKEN" 
    width="100%" 
    height="100%" 
    frameborder="0"
    allow="clipboard-write"
    title="CortexHeal Live Demo"
  ></iframe>
</div>
```

*Note: The `allow="clipboard-write"` permission is required if you want visitors to be able to test the "Copy as AI context" feature.*

## 4. Keep the Data Fresh (Cron Runner)

A dashboard is only impressive if things are happening. We have included a continuous background runner that sequentially triggers the built-in demo scenarios (Stuck Loop and Budget Overrun) to feed live data into your production database.

On your backend hosting environment, run this script as a continuous background worker:

```bash
python scripts/cron_demo_runner.py
```

This script runs in an infinite loop, executing a scenario, waiting 30 seconds, running the next, and then resting for 3 minutes. Any visitor viewing the iframe on your marketing site will see incidents trigger and resolve in real-time.
