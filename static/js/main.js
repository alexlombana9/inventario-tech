document.addEventListener('DOMContentLoaded', function () {

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

  // ── Auto-hide alerts ────────────────────────────────────────
  document.querySelectorAll('.alert-auto-hide').forEach(function (el) {
    setTimeout(function () {
      new bootstrap.Alert(el).close();
    }, 5000);
  });

  // ── Confirmar eliminación ───────────────────────────────────
  document.querySelectorAll('.form-delete').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const name = form.dataset.name || 'este elemento';
      if (!confirm('¿Eliminar "' + name + '"? Esta acción no se puede deshacer.')) {
        e.preventDefault();
      }
    });
  });

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

});
