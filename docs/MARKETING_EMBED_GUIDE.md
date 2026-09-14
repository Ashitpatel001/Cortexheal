# Live Public Demo Setup Guide

This guide explains how to set up the **CortexHeal Live Demo** on your public-facing marketing site.

Because CortexHeal provides an interactive dashboard powered by a real-time SSE (Server-Sent Events) stream, you can embed it directly into your marketing site. Potential customers can watch autonomous agents getting caught and safely recovered *live*, without signing up or touching a terminal.

## 1. Hosting Requirements

This guide assumes you have followed `DEPLOYMENT.md` to provision CortexHeal on a **bare-metal Linux server** using Caddy for reverse proxying and TLS. 

Your environment should be serving:
1. **Frontend App:** `https://app.YOURDOMAIN.com`
2. **Backend API:** `https://api.YOURDOMAIN.com`

*Do not use managed cloud providers (Render, Fly, etc.) for this specific deployment architecture.*

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

If you deployed using the bare-metal `docker-compose.prod.yml` configuration (as described in `DEPLOYMENT.md`), **this runner is already active**. It runs as a supervised, containerized background worker (`demo-runner`), ensuring visitors see a continuous stream of events if they stay on the page.

*Do not run the script manually on the server as an unsupervised process.*
