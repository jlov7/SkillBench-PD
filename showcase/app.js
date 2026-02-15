(() => {
  const mountHelpDrawer = () => {
    const helpButton = document.createElement('button');
    helpButton.className = 'help-trigger';
    helpButton.type = 'button';
    helpButton.textContent = 'Help';
    helpButton.setAttribute('aria-expanded', 'false');
    helpButton.setAttribute('aria-controls', 'quick-help-dialog');

    const helpDialog = document.createElement('aside');
    helpDialog.className = 'help-dialog';
    helpDialog.id = 'quick-help-dialog';
    helpDialog.setAttribute('aria-label', 'Quick guide');
    helpDialog.hidden = true;

    const head = document.createElement('div');
    head.className = 'help-head';
    const title = document.createElement('h2');
    title.textContent = 'Quick Guide';
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'help-close';
    closeButton.setAttribute('aria-label', 'Close help');
    closeButton.textContent = 'Close';
    head.append(title, closeButton);

    const helpText = document.createElement('p');
    helpText.textContent = 'New to this demo? Follow the guided path below.';

    const links = document.createElement('nav');
    links.className = 'help-links';
    links.setAttribute('aria-label', 'Guide links');
    const linkDefs = [
      ['Start with Guide', 'guide.html'],
      ['Understand Why It Matters', 'non-technical.html'],
      ['Inspect Technical Details', 'technical.html'],
      ['Review Evidence', 'evidence.html'],
    ];
    linkDefs.forEach(([label, href]) => {
      const a = document.createElement('a');
      a.href = href;
      a.textContent = label;
      links.appendChild(a);
    });

    helpDialog.append(head, helpText, links);
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
      navLinks.appendChild(helpButton);
    } else {
      document.body.appendChild(helpButton);
    }
    document.body.appendChild(helpDialog);

    let previousFocus = null;

    const closeDialog = () => {
      if (helpDialog.hidden) return;
      helpDialog.hidden = true;
      helpButton.setAttribute('aria-expanded', 'false');
      if (previousFocus instanceof HTMLElement) {
        previousFocus.focus();
      } else {
        helpButton.focus();
      }
    };

    const openDialog = () => {
      if (!helpDialog.hidden) return;
      previousFocus = document.activeElement;
      helpDialog.hidden = false;
      helpButton.setAttribute('aria-expanded', 'true');
      const firstFocusable = helpDialog.querySelector('button, a');
      if (firstFocusable instanceof HTMLElement) {
        firstFocusable.focus();
      }
    };

    helpButton.addEventListener('click', () => {
      if (helpDialog.hidden) {
        openDialog();
      } else {
        closeDialog();
      }
    });
    closeButton.addEventListener('click', closeDialog);

    document.addEventListener('keydown', (event) => {
      if (helpDialog.hidden) return;
      if (event.key === 'Escape') {
        closeDialog();
        return;
      }
      if (event.key !== 'Tab') return;

      const focusable = Array.from(helpDialog.querySelectorAll('button, a'));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        if (last instanceof HTMLElement) last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        if (first instanceof HTMLElement) first.focus();
      }
    });

    document.addEventListener('pointerdown', (event) => {
      if (helpDialog.hidden) return;
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!helpDialog.contains(target) && target !== helpButton) {
        closeDialog();
      }
    });
  };

  document.documentElement.classList.add('js');
  mountHelpDrawer();

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

    const statusEl = document.querySelector('[data-evidence-status]');
    if (statusEl) {
      statusEl.textContent = 'Loaded sample evidence dataset.';
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
      const statusEl = document.querySelector('[data-evidence-status]');
      if (fallback) {
        fallback.textContent = `Failed to load evidence data: ${err.message}`;
      }
      if (statusEl) {
        statusEl.textContent = 'Evidence data failed to load.';
      }
    });
})();
