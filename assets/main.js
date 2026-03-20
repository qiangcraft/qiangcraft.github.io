/* ═══════════════════════════════════════════════
   QiangCraft Blog — 共享脚本
═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── 滚动时导航栏加背景 ── */
  const hdr = document.getElementById('hdr');
  if (hdr) {
    window.addEventListener('scroll', () =>
      hdr.classList.toggle('scrolled', scrollY > 40), { passive: true });
  }

  /* ── 滚动显现动画 ── */
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  // 文章页首屏优先可读：避免 reveal 未触发导致正文长时间不可见
  if (document.querySelector('.post-layout')) {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }

  /* ── 分类过滤（仅首页） ── */
  const navBtns   = document.querySelectorAll('.nav-cat-btn');
  const topicRows = document.querySelectorAll('.topic-row[data-filter]');
  const heroCatLinks = document.querySelectorAll('[data-cat-jump]');
  const cards     = document.querySelectorAll('.post-card[data-cat]');
  const countEl   = document.getElementById('post-count');
  const emptyEl   = document.getElementById('empty-state');

  if (navBtns.length && cards.length) {
    function setFilter(cat) {
      navBtns.forEach(b => b.classList.toggle('active', b.dataset.cat === cat));
      let visible = 0;
      cards.forEach(card => {
        const show = cat === 'all' || card.dataset.cat === cat;
        card.classList.toggle('hidden', !show);
        if (show) visible++;
      });
      if (countEl) countEl.textContent = visible + ' 篇';
      if (emptyEl) emptyEl.classList.toggle('visible', visible === 0);
    }
    navBtns.forEach(b => b.addEventListener('click', () => {
      setFilter(b.dataset.cat);
      document.getElementById('posts-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
    topicRows.forEach(r => r.addEventListener('click', () => {
      setFilter(r.dataset.filter);
      document.getElementById('posts-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
    heroCatLinks.forEach(link => link.addEventListener('click', ev => {
      ev.preventDefault();
      const cat = link.getAttribute('data-cat-jump') || 'all';
      setFilter(cat);
      document.getElementById('posts-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
  }

  /* ── 文章页：Markdown 自动渲染 ── */
  document.querySelectorAll('script[type="text/markdown"]').forEach(src => {
    const targetId = src.dataset.target;
    const target = targetId ? document.getElementById(targetId) : src.parentElement;
    if (!target) return;
    const md = src.textContent || '';
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        target.innerHTML = window.marked.parse(md);
      } catch (err) {
        // 某些文章可能含有不完整围栏代码块，先补齐后重试，避免整页空白
        const fenceCount = (md.match(/```/g) || []).length;
        if (fenceCount % 2 === 1) {
          try {
            target.innerHTML = window.marked.parse(md + '\n```');
            return;
          } catch (_) {}
        }
        const safe = md
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
        target.innerHTML = '<pre class="code-block">' + safe + '</pre>';
      }
    } else {
      // 无解析器时保底显示纯文本，避免空白
      target.textContent = md;
    }
  });

  // 把 Markdown 生成的代码块统一成现有的 code-block 样式
  document.querySelectorAll('pre > code').forEach(code => {
    // 兼容 ```C++ 这类语言名，供 highlight.js 识别
    if (/\blanguage-c\+\+\b/i.test(code.className)) {
      code.className = code.className.replace(/\blanguage-c\+\+\b/ig, 'language-cpp');
    }
    const pre = code.parentElement;
    if (!pre || pre.classList.contains('code-block')) return;
    pre.classList.add('code-block');
    const langMatch = code.className.match(/language-([^\s]+)/);
    if (langMatch) {
      const label = document.createElement('span');
      label.className = 'lang-label';
      label.textContent = langMatch[1].toUpperCase();
      pre.insertBefore(label, code);
    }
  });

  /* ── 文章页：语法高亮（可选） ── */
  if (window.hljs && typeof window.hljs.highlightElement === 'function') {
    document.querySelectorAll('pre.code-block code').forEach(code => {
      window.hljs.highlightElement(code);
    });
  }

  /* ── 文章页：自动计算上一篇/下一篇（基于首页卡片） ── */
  if (document.querySelector('.post-layout')) {
    const prevLink = document.querySelector('.post-nav-link--prev');
    const nextLink = document.querySelector('.post-nav-link--next');
    const currentPath = location.pathname;
    const m = currentPath.match(/\/posts\/([^/]+)\/([^/]+\.html)$/);
    const currentCat = m ? m[1] : null;
    const currentFile = m ? m[2] : null;

    const setNav = (el, item, isPrev) => {
      if (!el) return;
      const label = el.querySelector('.post-nav-label');
      const title = el.querySelector('.post-nav-title');
      if (item) {
        el.href = './' + item.file;
        el.style.pointerEvents = '';
        el.style.opacity = '';
        if (label) label.textContent = isPrev ? '← 上一篇' : '下一篇 →';
        if (title) title.textContent = item.title;
      } else {
        el.href = '#';
        el.style.pointerEvents = 'none';
        el.style.opacity = '.45';
        if (label) label.textContent = isPrev ? '← 上一篇' : '下一篇 →';
        if (title) title.textContent = '暂无';
      }
    };

    if (currentCat && currentFile) {
      fetch('../../index.html')
        .then(r => r.text())
        .then(html => {
          const doc = new DOMParser().parseFromString(html, 'text/html');
          const cards = Array.from(doc.querySelectorAll('.post-card[data-cat]'));
          const posts = cards
            .map(card => {
              const href = card.getAttribute('href') || '';
              const mm = href.match(/^posts\/([^/]+)\/([^/]+\.html)$/);
              if (!mm) return null;
              if (mm[1] !== currentCat) return null;
              const dateText = (card.querySelector('.post-date')?.textContent || '').trim();
              const d = /^\d{4}-\d{2}-\d{2}$/.test(dateText) ? dateText : '1970-01-01';
              const title = (card.querySelector('.post-title')?.textContent || mm[2]).trim();
              return { file: mm[2], date: d, title };
            })
            .filter(Boolean)
            .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.file.localeCompare(b.file)));

          const idx = posts.findIndex(p => p.file === currentFile);
          if (idx >= 0) {
            const newer = idx > 0 ? posts[idx - 1] : null;
            const older = idx + 1 < posts.length ? posts[idx + 1] : null;
            setNav(prevLink, newer, true);
            setNav(nextLink, older, false);
          }
        })
        .catch(() => {
          // Keep fallback links already rendered in HTML.
        });
    }
  }

  /* ── 文章页：根据正文自动生成目录 ── */
  const toc = document.getElementById('toc');
  if (toc) {
    // 提升目录可读性（覆盖各文章页内联样式）
    const tocStyleId = 'toc-size-override';
    if (!document.getElementById(tocStyleId)) {
      const style = document.createElement('style');
      style.id = tocStyleId;
      style.textContent = `
        .toc-widget { max-height: calc(100vh - 120px) !important; }
        .toc-body { max-height: calc(100vh - 180px) !important; overflow-y: auto !important; overscroll-behavior: contain; }
        .toc-body::-webkit-scrollbar { width: 8px; }
        .toc-body::-webkit-scrollbar-thumb { background: rgba(148,163,184,.35); border-radius: 999px; }
        .toc-body::-webkit-scrollbar-track { background: transparent; }
        .toc-item { font-size: .76rem !important; line-height: 1.7 !important; }
        .toc-item--h3 { font-size: .72rem !important; }
      `;
      document.head.appendChild(style);
    }

    const headings = Array.from(document.querySelectorAll('.prose h2, .prose h3'));
    const slugCount = new Map();
    const toSlug = text => {
      const base = (text || '')
        .toLowerCase()
        .trim()
        .replace(/[^\w\u4e00-\u9fff\- ]+/g, '')
        .replace(/\s+/g, '-');
      const key = base || 'section';
      const n = (slugCount.get(key) || 0) + 1;
      slugCount.set(key, n);
      return n === 1 ? key : `${key}-${n}`;
    };

    if (headings.length) {
      const frag = document.createDocumentFragment();
      headings.forEach(h => {
        if (!h.id) h.id = toSlug(h.textContent);
        const a = document.createElement('a');
        a.href = `#${h.id}`;
        a.className = `toc-item${h.tagName === 'H3' ? ' toc-item--h3' : ''}`;
        a.textContent = h.textContent || '小节';
        frag.appendChild(a);
      });
      toc.innerHTML = '';
      toc.appendChild(frag);
    } else {
      toc.innerHTML = '';
    }
  }

  /* ── 文章页：代码块复制按钮 ── */
  document.querySelectorAll('pre.code-block').forEach(pre => {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = '复制';
    btn.onclick = () => {
      navigator.clipboard.writeText(pre.innerText).then(() => {
        btn.textContent = '已复制！';
        setTimeout(() => btn.textContent = '复制', 1800);
      });
    };
    pre.style.position = 'relative';
    pre.appendChild(btn);
  });

});
