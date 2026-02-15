(() => {
  const revealItems = Array.from(document.querySelectorAll('.reveal'));
  const prefersReducedMotion =
    'matchMedia' in window && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!prefersReducedMotion && 'IntersectionObserver' in window && revealItems.length > 0) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add('is-visible'));
  }

  const evidenceRoot = document.querySelector('[data-evidence-root]');
  if (!evidenceRoot) return;

  const fmt = (value, digits = 2) =>
    typeof value === 'number' ? value.toFixed(digits) : String(value ?? '—');

  const render = (data) => {
    const stats = data.summary || {};
    const cards = document.querySelector('[data-evidence-cards]');
    if (cards) {
      cards.replaceChildren();
      const cardDefs = [
        ['Modes', fmt(stats.mode_count, 0)],
        ['Tasks', fmt(stats.task_count, 0)],
        ['Records', fmt(stats.record_count, 0)],
        ['Best Cost Saver', stats.best_cost_mode || '—'],
      ];
      cardDefs.forEach(([label, value]) => {
        const card = document.createElement('article');
        card.className = 'metric-card';
        const labelP = document.createElement('p');
        labelP.className = 'metric-label';
        labelP.textContent = label;
        const valueP = document.createElement('p');
        valueP.className = 'metric-value';
        valueP.textContent = value;
        card.append(labelP, valueP);
        cards.appendChild(card);
      });
    }

    const table = document.querySelector('[data-aggregate-table]');
    if (table && Array.isArray(data.aggregates)) {
      table.replaceChildren();
      data.aggregates.forEach((row) => {
        const tr = document.createElement('tr');
        const values = [
          row.mode,
          fmt(row.latency_ms, 3),
          fmt(row.tokens_in, 2),
          fmt(row.rule_score, 3),
          fmt(row.cost_usd, 4),
        ];
        values.forEach((value) => {
          const td = document.createElement('td');
          td.textContent = value;
          tr.appendChild(td);
        });
        table.appendChild(tr);
      });
    }

    const commandEl = document.querySelector('[data-command]');
    if (commandEl && data.repro_command) {
      commandEl.textContent = data.repro_command;
    }
  };

  fetch('data/evidence.json')
    .then((res) => {
      if (!res.ok) throw new Error(`Could not load evidence.json (${res.status})`);
      return res.json();
    })
    .then((payload) => render(payload))
    .catch((err) => {
      const fallback = document.querySelector('[data-evidence-error]');
      if (fallback) {
        fallback.textContent = `Failed to load evidence data: ${err.message}`;
      }
    });
})();
