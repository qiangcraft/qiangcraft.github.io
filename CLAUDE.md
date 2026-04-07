# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QiangCraft.github.io is a static personal blog website focused on computer science, C++, robotics, and personal essays. The site is built with vanilla HTML, CSS, and JavaScript (no build system or framework), designed for simplicity and direct GitHub Pages deployment.

**Core Content Categories:**
- `personal` - 随笔 (Personal essays)
- `cs` - 计算机基础 (Computer Science fundamentals)
- `cpp` - C++ programming
- `robotics` - Robotics topics

## Architecture

### 1. Static Site Structure

The site is a single-page application (SPA) for the homepage with multi-page article views:

```
/index.html              # Homepage with all article cards
/posts/<category>/       # Article HTML files organized by category
  ├─ cpp/
  ├─ cs/
  ├─ personal/
  └─ robotics/
/assets/                 # Shared CSS, JS, and icons
/docs/                   # Markdown documentation files
/tools/                  # Python utilities for content management
```

### 2. Content Management System

**Article Template Flow:**
- Use `/posts/_template.html` as the base for new articles
- Articles are self-contained HTML files with inline styles
- Markdown content is embedded in `<script type="text/markdown">` tags and rendered client-side via marked.js

**Python Import Tool:**
- `tools/import_post.py` automates article import:
  - Copies HTML file to appropriate category folder
  - Extracts metadata (title, date, excerpt, read time)
  - Generates article card HTML
  - Inserts card into `index.html` at the correct position (chronologically)
  - Opens browser preview

**Usage:**
```bash
python3 tools/import_post.py --file path/to/article.html --cat robotics
```

### 3. Frontend Architecture

**Main JavaScript (`assets/main.js`):**
- **Category filtering:** Nav buttons + sidebar topic rows filter article cards by `data-cat` attribute
- **Tag filtering:** Tag pills filter by `data-tags` attribute
- **Markdown rendering:** Client-side rendering with marked.js for article content
- **Read time estimation:** Mixed Chinese/English word counting (300 chars/min Chinese, 200 words/min English)
- **View counting:** Uses countapi.xyz for page view tracking with localStorage fallback
- **WeChat QR modal:** Modal popup for contact QR code
- **TOC generation:** Auto-generates table of contents from `<h2>` and `<h3>` tags
- **Code copy buttons:** Adds copy-to-clipboard buttons to all code blocks

**CSS Organization:**
- `assets/style.css` contains global styles and CSS custom properties
- Inline `<style>` blocks in individual pages for page-specific layout

**Color Variables (in `:root`):**
```
--cs: #5B9CF6          (Computer Science blue)
--cpp: #A78BFA         (C++ purple)
--robotics: #34D399    (Robotics green)
--personal: #F0A04B    (Personal orange)
```

### 4. Article Synchronization Pattern

The homepage article cards are static HTML, but metadata is dynamically synced from actual article pages:
1. On page load, each card fetches its corresponding article HTML
2. Extracts `post-head-date`, `post-head-read`, and keywords meta tag
3. Updates card DOM to match source of truth (the article page)
4. Skipped on `file://` protocol to avoid CORS issues in local preview

This ensures article metadata stays consistent without a build step.

### 5. Navigation & Filtering Logic

**Multi-level filtering:**
- Nav category buttons set active category, deactivate tag filter
- Sidebar topic rows trigger same category filter with smooth scroll
- Tag pills toggle tag-based filtering, reset category to "all"
- Hero category links scroll to grid and set category filter

**Visibility rules:**
- All filtering toggles `.hidden` class on `.post-card` elements
- Empty state (`#empty-state`) shows when visible count is zero
- Counter (`#post-count`) always reflects current visible article count

## Common Development Tasks

### Adding a New Article

1. **Prepare the content:**
   - Write article in Markdown or directly in HTML
   - Choose appropriate category: `cs`, `cpp`, `robotics`, or `personal`

2. **Import using the tool (recommended):**
   ```bash
   python3 tools/import_post.py --file path/to/article.html --cat <category>
   ```
   This handles everything automatically.

3. **Manual method** (if tool fails):
   - Copy `posts/_template.html` to `posts/<category>/article-name.html`
   - Fill in `<title>`, meta description, article header, and content
   - Add card to `index.html` in chronological order within the `#posts-grid`
   - Match the card structure of existing cards

### Testing Locally

```bash
# Simple HTTP server (choose one):
python3 -m http.server 8000
# OR
npx serve
```

Then open `http://localhost:8000` in a browser.

**Note:** The view counter API and cross-page metadata sync don't work on `file://` protocol—always use a local server.

### Updating Article Metadata

If article date/title/excerpt changes:
1. Update the article HTML file (`posts/<category>/*.html`)
2. The homepage will auto-sync on next load (due to fetch logic in `main.js`)
3. For immediate update, manually edit the card HTML in `index.html`

### Adding New Categories

1. Add category definition to `tools/import_post.py` `CATEGORIES` dict
2. Add CSS custom property color in `assets/style.css`
3. Add nav button in `index.html` header nav
4. Add sidebar topic row in index sidebar
5. Create `posts/<new-category>/` directory

### Working with Markdown Content

Articles embed Markdown like this:
```html
<article class="prose" id="article-content"></article>
<script type="text/markdown" data-target="article-content">
# Your Markdown Here
Content...
</script>
```

The `main.js` script finds all `[type="text/markdown"]`, parses with marked.js, and injects HTML into the target element.

## Deployment

### GitHub Pages Setup
- Repo: `qiangcraft.github.io`
- Branch: `main` (deploy from root `/`)
- No build step required—push changes directly

### Pre-deployment Checklist
- Test all links work locally
- Verify images load (check relative paths)
- Confirm category filters work correctly
- Check responsive layout on mobile

### Git Workflow

```bash
# Make changes to articles or code
git add .
git commit -m "descriptive message"
git push origin main
```

GitHub Pages auto-deploys within 1-2 minutes.

## Code Style & Conventions

- **HTML:** Indent with 2 spaces, use semantic tags where possible
- **CSS:** Use CSS custom properties for colors, follow BEM-like naming for components
- **JavaScript:** ES6+ vanilla JS, no transpilation, avoid external dependencies beyond marked.js and highlight.js
- **Markdown:** Use standard GFM syntax, code blocks with language specifiers

## Key Files Reference

| File | Purpose |
|------|---------|
| `index.html` | Homepage with hero section and article grid |
| `assets/main.js` | All client-side interactivity |
| `assets/style.css` | Global styles and design system |
| `posts/_template.html` | Starter template for new articles |
| `tools/import_post.py` | Article import and card generation automation |

## External Dependencies

- **marked.js:** Markdown parsing (loaded from CDN in article pages)
- **highlight.js:** Syntax highlighting for code blocks (loaded from CDN)
- **Google Fonts:** IBM Plex Mono, Lora, Noto Sans SC
- **countapi.xyz:** View counter API (with localStorage fallback)

## Important Notes

- The homepage article count, dates, and read times should stay in sync with article pages—always update both if manually editing
- WeChat QR code image must exist at `/contact/wechat.jpeg` for modal to work
- All article URLs should use relative paths (`../../assets/style.css`, not `/assets/style.css`) to support subdirectory deployment
- When adding complex interactive visualizations (like the robot architecture pages), embed them as standalone HTML with inline JS
