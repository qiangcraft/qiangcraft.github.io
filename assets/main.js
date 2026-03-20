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

  /* ── 分类过滤（仅首页） ── */
  const navBtns   = document.querySelectorAll('.nav-cat-btn');
  const topicRows = document.querySelectorAll('.topic-row[data-filter]');
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
    navBtns.forEach(b => b.addEventListener('click', () => setFilter(b.dataset.cat)));
    topicRows.forEach(r => r.addEventListener('click', () => {
      setFilter(r.dataset.filter);
      document.getElementById('posts-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
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
