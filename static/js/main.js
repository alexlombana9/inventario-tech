// ── Theme: aplicar antes de DOMContentLoaded para evitar flash ──
(function () {
  var saved = localStorage.getItem('techstock_theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();

// ── Toast notification system (global) ────────────────────────────
window.showToast = function(message, type) {
  type = type || 'success';
  var container = document.querySelector('.toast-container');
  if (!container) return;
  var icons = {
    success: 'bi-check-circle-fill',
    danger: 'bi-exclamation-triangle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill'
  };
  var toast = document.createElement('div');
  toast.className = 'toast-notification toast-' + type;
  toast.innerHTML = '<i class="bi ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span><button class="toast-close">&times;</button>';
  toast.querySelector('.toast-close').addEventListener('click', function() {
    toast.classList.add('removing');
    setTimeout(function() { toast.remove(); }, 250);
  });
  container.appendChild(toast);
  var timeout = Math.max(3000, message.length * 60);
  setTimeout(function() {
    if (toast.parentElement) {
      toast.classList.add('removing');
      setTimeout(function() { toast.remove(); }, 250);
    }
  }, timeout);
};

document.addEventListener('DOMContentLoaded', function () {

  // ── Theme toggle ───────────────────────────────────────────
  var themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    function updateThemeIcon() {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      themeBtn.innerHTML = isDark
        ? '<i class="bi bi-sun-fill"></i>'
        : '<i class="bi bi-moon-fill"></i>';
      themeBtn.title = isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
    }
    updateThemeIcon();

    themeBtn.addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('techstock_theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('techstock_theme', 'dark');
      }
      updateThemeIcon();
    });
  }

  // ── Sidebar toggle ──────────────────────────────────────────
  const toggle   = document.getElementById('sidebarToggle');
  const sidebar  = document.getElementById('sidebar');
  const main     = document.getElementById('mainContent');
  const backdrop = document.getElementById('sidebarBackdrop');

  function isMobile() { return window.innerWidth <= 768; }

  function openMobileSidebar() {
    sidebar.classList.add('mobile-open');
    backdrop.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeMobileSidebar() {
    sidebar.classList.remove('mobile-open');
    backdrop.classList.remove('show');
    document.body.style.overflow = '';
  }

  function toggleDesktopSidebar() {
    sidebar.classList.toggle('collapsed');
    main.classList.toggle('collapsed');
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      if (isMobile()) {
        sidebar.classList.contains('mobile-open') ? closeMobileSidebar() : openMobileSidebar();
      } else {
        toggleDesktopSidebar();
      }
    });
  }

  // Cerrar al hacer clic en el backdrop
  if (backdrop) {
    backdrop.addEventListener('click', closeMobileSidebar);
  }

  // Cerrar sidebar mobile al hacer clic en un nav-link (navegación)
  if (sidebar) {
    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
      link.addEventListener('click', function () {
        if (isMobile()) closeMobileSidebar();
      });
    });
  }

  // Re-ajustar al rotar pantalla
  window.addEventListener('resize', function () {
    if (!isMobile()) {
      closeMobileSidebar();
      backdrop.classList.remove('show');
      document.body.style.overflow = '';
    }
  });

  // ── Auto-hide alerts + convert to toasts ─────────────────────
  document.querySelectorAll('.alert-auto-hide').forEach(function (el) {
    // Convert server-rendered flash alerts into toast notifications
    var msg = el.textContent.trim();
    var toastType = 'info';
    if (el.classList.contains('alert-success')) toastType = 'success';
    else if (el.classList.contains('alert-danger')) toastType = 'danger';
    else if (el.classList.contains('alert-warning')) toastType = 'warning';
    if (msg && window.showToast) {
      window.showToast(msg, toastType);
    }
    // Still close the inline alert for backward compatibility
    setTimeout(function () {
      new bootstrap.Alert(el).close();
    }, 500);
  });

  // ── Confirmar eliminación (modal o fallback a confirm) ───────
  var deleteModal = document.getElementById('confirmDeleteModal');
  if (deleteModal) {
    var bsDeleteModal = new bootstrap.Modal(deleteModal);
    var pendingDeleteForm = null;

    document.addEventListener('submit', function(e) {
      var form = e.target.closest('.form-delete');
      if (!form) return;
      e.preventDefault();
      pendingDeleteForm = form;
      var itemName = form.dataset.name || 'este elemento';
      var nameEl = deleteModal.querySelector('.confirm-item-name');
      if (nameEl) nameEl.textContent = itemName;
      bsDeleteModal.show();
    });

    var confirmBtn = deleteModal.querySelector('.btn-confirm-delete');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', function() {
        if (pendingDeleteForm) {
          pendingDeleteForm.submit();
          pendingDeleteForm = null;
        }
        bsDeleteModal.hide();
      });
    }
  } else {
    // Fallback: use native confirm() when modal is not in the DOM
    document.querySelectorAll('.form-delete').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        var name = form.dataset.name || 'este elemento';
        if (!confirm('¿Eliminar "' + name + '"? Esta acción no se puede deshacer.')) {
          e.preventDefault();
        }
      });
    });
  }

  // ── Stock info en formulario de inventario ──────────────────
  const productoSelect = document.getElementById('producto_id');
  const stockInfo      = document.getElementById('stock-info');
  const precioCostoInput = document.getElementById('precio_unitario');

  if (productoSelect) {
    productoSelect.addEventListener('change', function () {
      const opt    = this.options[this.selectedIndex];
      const stock  = opt.dataset.stock;
      const unidad = opt.dataset.unidad;
      const minimo = opt.dataset.minimo;
      const costo  = opt.dataset.costo;

      if (stockInfo && stock !== undefined) {
        stockInfo.innerHTML =
          '<span class="me-3"><strong>Stock actual:</strong> ' + parseFloat(stock).toFixed(2) + ' ' + unidad + '</span>' +
          '<span><strong>Mínimo:</strong> ' + parseFloat(minimo).toFixed(2) + ' ' + unidad + '</span>';
        stockInfo.classList.remove('d-none');
      }

      if (precioCostoInput && costo && (precioCostoInput.value === '0' || precioCostoInput.value === '')) {
        precioCostoInput.value = parseFloat(costo).toFixed(2);
      }
    });
  }

  // ── Searchable Select ────────────────────────────────────────
  // Mejora cualquier <select data-searchable> con un campo de busqueda
  // que filtra opciones por texto (nombre, codigo, referencia).
  document.querySelectorAll('select[data-searchable]').forEach(function (select) {
    var placeholder = select.dataset.searchPlaceholder || 'Buscar...';

    // Guardar opciones originales (excluyendo el placeholder)
    var allOptions = [];
    for (var i = 0; i < select.options.length; i++) {
      allOptions.push({
        value: select.options[i].value,
        text: select.options[i].textContent,
        html: select.options[i].outerHTML,
        isPlaceholder: select.options[i].value === ''
      });
    }

    // Crear el input de busqueda
    var searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control searchable-select-input';
    searchInput.placeholder = placeholder;
    searchInput.setAttribute('autocomplete', 'off');

    // Crear el wrapper
    var wrapper = document.createElement('div');
    wrapper.className = 'searchable-select-wrapper';

    // Icono de busqueda dentro del input
    var iconWrapper = document.createElement('div');
    iconWrapper.className = 'searchable-select-icon';
    iconWrapper.innerHTML = '<i class="bi bi-search"></i>';

    // Contador de resultados
    var counter = document.createElement('small');
    counter.className = 'searchable-select-count text-muted';
    counter.style.display = 'none';

    // Insertar antes del select
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(iconWrapper);
    wrapper.appendChild(searchInput);
    wrapper.appendChild(counter);
    wrapper.appendChild(select);

    // Funcion de filtrado
    function filterOptions() {
      var term = searchInput.value.toLowerCase().trim();
      var matchCount = 0;
      var totalOptions = 0;

      // Limpiar select manteniendo la opcion placeholder
      while (select.options.length > 0) {
        select.remove(0);
      }

      for (var j = 0; j < allOptions.length; j++) {
        var opt = allOptions[j];
        if (opt.isPlaceholder) {
          // Siempre agregar el placeholder
          var placeholderOpt = document.createElement('option');
          placeholderOpt.value = '';
          placeholderOpt.textContent = opt.text;
          select.appendChild(placeholderOpt);
          continue;
        }

        totalOptions++;
        if (term === '' || opt.text.toLowerCase().indexOf(term) !== -1) {
          // Insertar la opcion usando un template temporal para preservar data-attributes
          var temp = document.createElement('template');
          temp.innerHTML = opt.html;
          select.appendChild(temp.content.firstChild);
          matchCount++;
        }
      }

      // Mostrar contador si hay filtro activo
      if (term !== '') {
        counter.textContent = matchCount + ' de ' + totalOptions + ' productos';
        counter.style.display = 'block';
      } else {
        counter.style.display = 'none';
      }

      // Si solo queda una opcion (ademas del placeholder), seleccionarla
      if (matchCount === 1 && select.options.length === 2) {
        select.selectedIndex = 1;
        select.dispatchEvent(new Event('change'));
      }
    }

    // Eventos
    searchInput.addEventListener('input', filterOptions);

    // Limpiar busqueda con Escape
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        filterOptions();
        searchInput.blur();
      }
    });

    // Prevenir submit del form al presionar Enter en el campo de busqueda
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
      }
    });
  });

  // ── Filtros con auto-submit ─────────────────────────────────
  document.querySelectorAll('.auto-submit').forEach(function (el) {
    el.addEventListener('change', function () {
      this.closest('form').submit();
    });
  });

  // ── Modal edición de categorías ─────────────────────────────
  document.querySelectorAll('.btn-edit-categoria').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const id   = this.dataset.id;
      const nom  = this.dataset.nombre;
      const desc = this.dataset.descripcion;
      const idEl   = document.getElementById('edit-cat-id');
      const nomEl  = document.getElementById('edit-cat-nombre');
      const descEl = document.getElementById('edit-cat-descripcion');
      const formEl = document.getElementById('edit-cat-form');
      if (idEl)   idEl.value   = id;
      if (nomEl)  nomEl.value  = nom;
      if (descEl) descEl.value = desc;
      if (formEl) formEl.action = '/categorias/' + id + '/editar';
    });
  });

  // ── Form submission loading states ──────────────────────────
  document.querySelectorAll('form').forEach(function(form) {
    if (form.classList.contains('form-delete') || form.dataset.noLoading) return;
    form.addEventListener('submit', function() {
      var btn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (btn && !btn.disabled) {
        btn.dataset.originalHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Procesando...';
        btn.disabled = true;
        // Safety timeout — re-enable after 10s in case navigation fails
        setTimeout(function() {
          if (btn.dataset.originalHtml) {
            btn.disabled = false;
            btn.innerHTML = btn.dataset.originalHtml;
          }
        }, 10000);
      }
    });
  });

  // ── Clickable table rows ────────────────────────────────────
  document.addEventListener('click', function(e) {
    var row = e.target.closest('tr[data-href]');
    if (row && !e.target.closest('a, button, form, input, .form-delete')) {
      window.location.href = row.dataset.href;
    }
  });

  // ── Table column sorting ────────────────────────────────────
  document.addEventListener('click', function(e) {
    var th = e.target.closest('th[data-sortable]');
    if (!th) return;
    var table = th.closest('table');
    if (!table || !table.tBodies[0]) return;
    var idx = Array.from(th.parentElement.children).indexOf(th);
    var rows = Array.from(table.tBodies[0].rows);
    var asc = th.dataset.sortDir !== 'asc';

    // Reset other headers
    th.parentElement.querySelectorAll('th[data-sortable]').forEach(function(h) {
      if (h !== th) delete h.dataset.sortDir;
    });

    rows.sort(function(a, b) {
      var av = a.cells[idx] ? a.cells[idx].textContent.trim() : '';
      var bv = b.cells[idx] ? b.cells[idx].textContent.trim() : '';
      // Try numeric comparison
      var an = parseFloat(av.replace(/[^0-9.,\-]/g, '').replace(',', '.'));
      var bn = parseFloat(bv.replace(/[^0-9.,\-]/g, '').replace(',', '.'));
      if (!isNaN(an) && !isNaN(bn)) {
        return asc ? an - bn : bn - an;
      }
      return asc ? av.localeCompare(bv, 'es', {numeric: true}) : bv.localeCompare(av, 'es', {numeric: true});
    });

    rows.forEach(function(r) { table.tBodies[0].appendChild(r); });
    th.dataset.sortDir = asc ? 'asc' : 'desc';
  });

  // ── Search input clear buttons ──────────────────────────────
  document.querySelectorAll('.input-clear-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var input = btn.parentElement.querySelector('input');
      if (input) {
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
      }
    });
  });

  // ── Sidebar active scroll into view ─────────────────────────
  var activeNav = document.querySelector('.sidebar .nav-link.active');
  if (activeNav) {
    activeNav.scrollIntoView({ block: 'center', behavior: 'instant' });
  }

  // ── Form validation (Bootstrap) ─────────────────────────────
  document.querySelectorAll('form[data-validate]').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

});

// ── Command Palette (Ctrl+K) ──────────────────────────────────
(function() {
  var overlay = document.getElementById('commandPaletteOverlay');
  if (!overlay) return;
  var input = overlay.querySelector('.command-palette-input');
  var results = overlay.querySelector('.command-palette-results');
  var activeIdx = -1;

  // Navigation items from sidebar
  var navItems = [];
  document.querySelectorAll('.sidebar .nav-link[href]').forEach(function(link) {
    var text = link.querySelector('span');
    var icon = link.querySelector('i');
    if (text && text.textContent.trim()) {
      navItems.push({
        label: text.textContent.trim(),
        href: link.getAttribute('href'),
        icon: icon ? icon.className : 'bi bi-arrow-right',
        type: 'nav'
      });
    }
  });

  // Quick actions
  var quickActions = [
    { label: 'Nuevo Producto', href: '/productos/nuevo', icon: 'bi bi-plus-circle', type: 'action' },
    { label: 'Nueva Venta (POS)', href: '/ventas/pos', icon: 'bi bi-cart-plus', type: 'action' },
    { label: 'Nuevo Cliente', href: '/clientes/nuevo', icon: 'bi bi-person-plus', type: 'action' },
    { label: 'Nueva Deuda', href: '/deudas/nueva', icon: 'bi bi-cash-stack', type: 'action' },
    { label: 'Nueva Factura', href: '/facturas/nueva', icon: 'bi bi-receipt', type: 'action' },
    { label: 'Nuevo Gasto', href: '/gastos/nuevo', icon: 'bi bi-wallet2', type: 'action' },
    { label: 'Entrada Inventario', href: '/inventario/entrada', icon: 'bi bi-box-arrow-in-down', type: 'action' },
    { label: 'Abrir Caja', href: '/caja/abrir', icon: 'bi bi-unlock', type: 'action' }
  ];

  var allItems = quickActions.concat(navItems);

  function openPalette() {
    overlay.classList.add('active');
    input.value = '';
    activeIdx = -1;
    renderResults('');
    setTimeout(function() { input.focus(); }, 50);
  }

  function closePalette() {
    overlay.classList.remove('active');
    input.value = '';
  }

  function renderResults(query) {
    query = query.toLowerCase().trim();
    var filtered = allItems.filter(function(item) {
      return !query || item.label.toLowerCase().includes(query);
    });

    if (filtered.length === 0) {
      results.innerHTML = '<div class="command-palette-empty"><i class="bi bi-search me-2"></i>Sin resultados para "' + query + '"</div>';
      return;
    }

    var html = '';
    var actions = filtered.filter(function(i) { return i.type === 'action'; });
    var navs = filtered.filter(function(i) { return i.type === 'nav'; });
    var idx = 0;

    if (actions.length) {
      html += '<div class="command-palette-group">Acciones rapidas</div>';
      actions.forEach(function(item) {
        html += '<div class="command-palette-item" data-idx="' + idx + '" data-href="' + item.href + '"><span class="cp-icon"><i class="' + item.icon + '"></i></span><span class="cp-label">' + item.label + '</span></div>';
        idx++;
      });
    }
    if (navs.length) {
      html += '<div class="command-palette-group">Navegacion</div>';
      navs.forEach(function(item) {
        html += '<div class="command-palette-item" data-idx="' + idx + '" data-href="' + item.href + '"><span class="cp-icon"><i class="' + item.icon + '"></i></span><span class="cp-label">' + item.label + '</span></div>';
        idx++;
      });
    }

    results.innerHTML = html;
    activeIdx = -1;
  }

  function navigateToItem(el) {
    if (el && el.dataset.href) {
      closePalette();
      window.location.href = el.dataset.href;
    }
  }

  function setActive(idx) {
    var items = results.querySelectorAll('.command-palette-item');
    items.forEach(function(i) { i.classList.remove('active'); });
    if (idx >= 0 && idx < items.length) {
      items[idx].classList.add('active');
      items[idx].scrollIntoView({ block: 'nearest' });
      activeIdx = idx;
    }
  }

  // Button click: #openCommandPalette
  var openBtn = document.getElementById('openCommandPalette');
  if (openBtn) {
    openBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      openPalette();
    });
  }

  // Keyboard shortcut: Ctrl+K or /
  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && !e.target.matches('input, textarea, select, [contenteditable]'))) {
      e.preventDefault();
      if (overlay.classList.contains('active')) closePalette();
      else openPalette();
    }
    if (e.key === 'Escape' && overlay.classList.contains('active')) {
      closePalette();
    }
  });

  // Input filtering
  input.addEventListener('input', function() {
    renderResults(input.value);
  });

  // Arrow keys + Enter
  input.addEventListener('keydown', function(e) {
    var items = results.querySelectorAll('.command-palette-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive(Math.min(activeIdx + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive(Math.max(activeIdx - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      var active = results.querySelector('.command-palette-item.active');
      if (active) navigateToItem(active);
      else if (items.length) navigateToItem(items[0]);
    }
  });

  // Click on item
  results.addEventListener('click', function(e) {
    var item = e.target.closest('.command-palette-item');
    if (item) navigateToItem(item);
  });

  // Click overlay to close
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closePalette();
  });
})();
