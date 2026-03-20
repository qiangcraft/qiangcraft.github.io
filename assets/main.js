/* ═══════════════════════════════════════════════
   QiangCraft Blog — 共享脚本
═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  function estimateReadMinutes(text) {
    const src = text || '';
    const cjkCount = (src.match(/[\u4e00-\u9fff]/g) || []).length;
    const wordCount = (src.match(/[A-Za-z0-9_]+/g) || []).length;
    // Mixed-language estimate:
    // Chinese reading speed ~300 chars/min, English ~200 words/min.
    const minutes = (cjkCount / 300) + (wordCount / 200);
    return Math.max(1, Math.ceil(minutes));
  }

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

    // 首页卡片与文章页元信息对齐：自动同步阅读时长/日期
    // 本地 file:// 预览下跨文件 fetch 不稳定，跳过动态覆盖，保留静态值
    if (location.protocol !== 'file:') {
      cards.forEach(card => {
        const href = card.getAttribute('href') || '';
        if (!/^posts\/.+\.html$/.test(href)) return;
        fetch(href)
          .then(r => r.text())
          .then(html => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const postDate = (doc.querySelector('.post-head-date')?.textContent || '').trim();
            const dateEl = card.querySelector('.post-date');
            if (postDate && dateEl) dateEl.textContent = postDate;

            const mdText = doc.querySelector('script[type="text/markdown"]')?.textContent || '';
            const mins = mdText ? estimateReadMinutes(mdText) : null;
            const readText = mins ? `约 ${mins} 分钟` : ((doc.querySelector('.post-head-read')?.textContent || '').trim());
            const metaEl = card.querySelector('.post-meta');
            if (readText && metaEl) {
              const raw = (metaEl.textContent || '').trim();
              const parts = raw.split('·').map(s => s.trim()).filter(Boolean);
              metaEl.textContent = parts.length > 1 ? [readText, ...parts.slice(1)].join(' · ') : readText;
            }
          })
          .catch(() => {});
      });
    }
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

  /* ── 文章页：阅读时长自动估算 ── */
  if (document.querySelector('.post-layout') && location.protocol !== 'file:') {
    const readEl = document.querySelector('.post-head-read');
    if (readEl) {
      // 优先使用 Markdown 源，拿不到时回退到渲染后的正文文本
      const mdEl = document.querySelector('script[type="text/markdown"]');
      const sourceText = mdEl ? (mdEl.textContent || '') : (document.querySelector('.prose')?.innerText || '');
      const mins = estimateReadMinutes(sourceText);
      readEl.textContent = `约 ${mins} 分钟`;
    }
  }

  /* ── 首页：微信二维码弹窗 ── */
  const wechatModal = document.getElementById('wechat-modal');
  if (wechatModal) {
    const openers = document.querySelectorAll('[data-open-wechat]');
    const closeBtn = document.getElementById('wechat-close');
    const qr = document.getElementById('wechat-qr');
    const tip = document.getElementById('wechat-tip');

    const openModal = () => {
      wechatModal.classList.add('is-open');
      wechatModal.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    };
    const closeModal = () => {
      wechatModal.classList.remove('is-open');
      wechatModal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    };

    openers.forEach(el => el.addEventListener('click', e => {
      e.preventDefault();
      openModal();
    }));
    closeBtn?.addEventListener('click', closeModal);
    wechatModal.addEventListener('click', e => {
      if (e.target === wechatModal) closeModal();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && wechatModal.classList.contains('is-open')) closeModal();
    });
    qr?.addEventListener('error', () => {
      if (tip) tip.textContent = '未找到二维码图片：contact/wechat.jpeg';
    });
  }

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
