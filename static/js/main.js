// Sidebar toggle
document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('mainContent');

  if (toggle) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
      main.classList.toggle('collapsed');
    });
  }

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-auto-hide');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Confirm delete actions
  const deleteForms = document.querySelectorAll('.form-delete');
  deleteForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const name = form.dataset.name || 'este elemento';
      if (!confirm(`¿Estás seguro de que deseas eliminar "${name}"? Esta acción no se puede deshacer.`)) {
        e.preventDefault();
      }
    });
  });

  // Producto stock info on inventory form
  const productoSelect = document.getElementById('producto_id');
  const stockInfo = document.getElementById('stock-info');

  if (productoSelect && stockInfo) {
    productoSelect.addEventListener('change', function () {
      const option = this.options[this.selectedIndex];
      const stock = option.dataset.stock;
      const unidad = option.dataset.unidad;
      const minimo = option.dataset.minimo;
      if (stock !== undefined) {
        stockInfo.innerHTML = `
          <span class="me-3"><strong>Stock actual:</strong> ${parseFloat(stock).toFixed(2)} ${unidad}</span>
          <span><strong>Mínimo:</strong> ${parseFloat(minimo).toFixed(2)} ${unidad}</span>
        `;
        stockInfo.classList.remove('d-none');
      } else {
        stockInfo.classList.add('d-none');
      }
    });
  }

  // Precio de costo auto-fill en entradas
  const productoSelectFull = document.getElementById('producto_id');
  const precioCostoInput = document.getElementById('precio_unitario');
  if (productoSelectFull && precioCostoInput) {
    productoSelectFull.addEventListener('change', function () {
      const option = this.options[this.selectedIndex];
      const costo = option.dataset.costo;
      if (costo && precioCostoInput.value === '0' || precioCostoInput.value === '') {
        precioCostoInput.value = parseFloat(costo).toFixed(2);
      }
    });
  }

  // Filtros con auto-submit
  const autoSubmitSelects = document.querySelectorAll('.auto-submit');
  autoSubmitSelects.forEach(function (el) {
    el.addEventListener('change', function () {
      this.closest('form').submit();
    });
  });

  // Modal de edición de categorías
  const editButtons = document.querySelectorAll('.btn-edit-categoria');
  editButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      const nombre = this.dataset.nombre;
      const desc = this.dataset.descripcion;
      document.getElementById('edit-cat-id').value = id;
      document.getElementById('edit-cat-nombre').value = nombre;
      document.getElementById('edit-cat-descripcion').value = desc;
      document.getElementById('edit-cat-form').action = `/categorias/${id}/editar`;
    });
  });
});
