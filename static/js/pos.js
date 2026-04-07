/**
 * TechStock — Punto de Venta (POS)
 * Cart management, product search, payment handling.
 * Supports manual price editing per item.
 * Uses event delegation — no inline onclick handlers.
 */
const cart = [];
const formatter = new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP',
  minimumFractionDigits: 0, maximumFractionDigits: 0
});

function formatMoney(v) { return formatter.format(v); }

function addToCart(id, code, name, price, cost, stock, unit, ref) {
  const existing = cart.find(i => i.producto_id === id);
  if (existing) {
    if (existing.cantidad >= stock) { alert('Stock insuficiente'); return; }
    existing.cantidad++;
  } else {
    cart.push({
      producto_id: id, codigo: code, nombre: name,
      precio_unitario: price, precio_original: price, precio_costo: cost,
      cantidad: 1, stock: stock, descuento: 0,
      referencia: ref || ''
    });
  }
  renderCart();
}

function removeFromCart(idx) { cart.splice(idx, 1); renderCart(); }

function updateQty(idx, delta) {
  const item = cart[idx];
  const newQty = item.cantidad + delta;
  if (newQty <= 0) { removeFromCart(idx); return; }
  if (newQty > item.stock) { alert('Stock insuficiente'); return; }
  item.cantidad = newQty;
  renderCart();
}

function setQty(idx, val) {
  const item = cart[idx];
  const qty = parseFloat(val) || 0;
  if (qty <= 0) { removeFromCart(idx); return; }
  if (qty > item.stock) { alert('Stock insuficiente'); item.cantidad = item.stock; }
  else { item.cantidad = qty; }
  renderCart();
}

function setPrice(idx, val) {
  const item = cart[idx];
  const price = parseFloat(val) || 0;
  if (price < 0) return;
  item.precio_unitario = price;
  renderCart();
}

function clearCart() { cart.length = 0; renderCart(); localStorage.removeItem('techstock_pos_draft'); }

function _escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderCart() {
  const container = document.getElementById('cartItems');
  const btn = document.getElementById('btnPagar');

  if (cart.length === 0) {
    container.innerHTML = '<div class="text-center text-muted py-4" id="emptyCart">' +
      '<i class="bi bi-cart-x" style="font-size:2rem"></i>' +
      '<p class="mt-2 mb-0">Carrito vacio</p></div>';
    document.getElementById('cartTotal').textContent = '$0';
    document.getElementById('cartGanancia').textContent = '$0';
    btn.disabled = true;
    return;
  }

  btn.disabled = false;
  var html = '';
  var total = 0;
  var gananciaTotal = 0;
  cart.forEach(function(item, idx) {
    var sub = item.cantidad * item.precio_unitario;
    var ganancia = (item.precio_unitario - item.precio_costo) * item.cantidad;
    total += sub;
    gananciaTotal += ganancia;
    var precioModificado = item.precio_unitario !== item.precio_original;
    var precioOrigLabel = precioModificado
      ? '<span class="precio-original"><s>' + formatMoney(item.precio_original) + '</s> &rarr;</span> '
      : '';
    html += '<div class="cart-item" data-idx="' + idx + '">' +
      '<div class="qty-control">' +
        '<button class="btn btn-sm btn-outline-secondary" data-action="qty-down">-</button>' +
        '<input type="number" value="' + item.cantidad + '" min="0.01" max="' + item.stock + '" step="any" data-action="qty-input">' +
        '<button class="btn btn-sm btn-outline-secondary" data-action="qty-up">+</button>' +
      '</div>' +
      '<div class="item-info">' +
        '<div class="item-name">' + _escapeHtml(item.nombre) + '</div>' +
        '<div class="item-meta">' + _escapeHtml(item.codigo) +
          (item.referencia ? ' | Ref: ' + _escapeHtml(item.referencia) : '') +
        '</div>' +
        '<div class="item-price-edit">' +
          '<i class="bi bi-pencil-fill price-edit-icon"></i>' +
          precioOrigLabel +
          '<input type="number" class="form-control form-control-sm price-input' +
                 (precioModificado ? ' price-modified' : '') + '" ' +
                 'value="' + item.precio_unitario + '" min="0" step="any" ' +
                 'data-action="price-input" title="Precio de venta — click para editar">' +
          '<span class="price-unit">c/u</span>' +
        '</div>' +
      '</div>' +
      '<div class="text-end">' +
        '<div class="item-subtotal">' + formatMoney(sub) + '</div>' +
        '<div class="item-ganancia ' + (ganancia >= 0 ? 'text-success' : 'text-danger') + '">' +
          (ganancia >= 0 ? '+' : '') + formatMoney(ganancia) +
        '</div>' +
      '</div>' +
      '<button class="remove-btn" data-action="remove"><i class="bi bi-x-lg"></i></button>' +
    '</div>';
  });
  container.innerHTML = html;
  document.getElementById('cartTotal').textContent = formatMoney(total);
  var gananciaEl = document.getElementById('cartGanancia');
  if (gananciaEl) {
    gananciaEl.textContent = formatMoney(gananciaTotal);
    gananciaEl.className = 'amount ' + (gananciaTotal >= 0 ? 'text-success' : 'text-danger');
  }
  updateCambio();
  // Persistir borrador en localStorage (incluye notas)
  var notasEl = document.getElementById('ventaNotas');
  var draftData = { cart: cart, notas: notasEl ? notasEl.value : '' };
  if (cart.length > 0) {
    localStorage.setItem('techstock_pos_draft', JSON.stringify(draftData));
  } else {
    localStorage.removeItem('techstock_pos_draft');
  }
}

function updateCambio() {
  var total = cart.reduce(function(s, i) { return s + i.cantidad * i.precio_unitario; }, 0);
  var recibido = parseFloat(document.getElementById('montoRecibido').value) || 0;
  var cambio = Math.max(0, recibido - total);
  document.getElementById('cambioDisplay').textContent = formatMoney(cambio);
}

// ── Event Listeners (initialized on DOMContentLoaded) ──
document.addEventListener('DOMContentLoaded', function() {
  // Restaurar borrador desde localStorage
  var draftRaw = localStorage.getItem('techstock_pos_draft');
  if (draftRaw) {
    try {
      var draft = JSON.parse(draftRaw);
      var savedCart = Array.isArray(draft) ? draft : (draft.cart || []);
      var savedNotas = (!Array.isArray(draft) && draft.notas) ? draft.notas : '';
      if (savedCart.length > 0) {
        savedCart.forEach(function(item) { cart.push(item); });
        var notasEl = document.getElementById('ventaNotas');
        if (notasEl && savedNotas) { notasEl.value = savedNotas; }
        renderCart();
        // Indicador visual de borrador restaurado
        var header = document.querySelector('.cart-header span');
        if (header) {
          var badge = document.createElement('span');
          badge.className = 'badge bg-warning text-dark ms-2';
          badge.style.fontSize = '0.7rem';
          badge.textContent = 'Borrador recuperado';
          header.appendChild(badge);
          setTimeout(function() { badge.remove(); }, 3000);
        }
      }
    } catch(e) { localStorage.removeItem('techstock_pos_draft'); }
  }

  // Guardar notas en borrador al escribir
  var ventaNotasEl = document.getElementById('ventaNotas');
  if (ventaNotasEl) {
    ventaNotasEl.addEventListener('input', function() {
      if (cart.length > 0) {
        var draftData = { cart: cart, notas: ventaNotasEl.value };
        localStorage.setItem('techstock_pos_draft', JSON.stringify(draftData));
      }
    });
  }

  // Cart event delegation — handles all cart item interactions
  var cartContainer = document.getElementById('cartItems');
  if (cartContainer) {
    cartContainer.addEventListener('click', function(e) {
      var target = e.target.closest('[data-action]');
      if (!target) return;
      var cartItem = target.closest('[data-idx]');
      if (!cartItem) return;
      var idx = parseInt(cartItem.dataset.idx);
      var action = target.dataset.action;

      if (action === 'qty-down') updateQty(idx, -1);
      else if (action === 'qty-up') updateQty(idx, 1);
      else if (action === 'remove') removeFromCart(idx);
    });

    cartContainer.addEventListener('change', function(e) {
      var target = e.target;
      var action = target.dataset.action;
      if (!action) return;
      var cartItem = target.closest('[data-idx]');
      if (!cartItem) return;
      var idx = parseInt(cartItem.dataset.idx);

      if (action === 'qty-input') setQty(idx, target.value);
      else if (action === 'price-input') setPrice(idx, target.value);
    });

    // Stop click propagation on price inputs to prevent cart item selection
    cartContainer.addEventListener('click', function(e) {
      if (e.target.dataset.action === 'price-input') e.stopPropagation();
    });
  }

  // Product search filter (name, code, reference)
  document.getElementById('productSearch').addEventListener('input', function() {
    var q = this.value.toLowerCase();
    document.querySelectorAll('.product-item').forEach(function(el) {
      var name = el.dataset.name.toLowerCase();
      var code = el.dataset.code.toLowerCase();
      var ref = (el.dataset.ref || '').toLowerCase();
      el.style.display = (name.includes(q) || code.includes(q) || ref.includes(q)) ? '' : 'none';
    });
  });

  // Click to add product
  document.querySelectorAll('.product-item').forEach(function(el) {
    el.addEventListener('click', function() {
      addToCart(
        parseInt(el.dataset.id), el.dataset.code, el.dataset.name,
        parseFloat(el.dataset.price), parseFloat(el.dataset.cost || '0'),
        parseFloat(el.dataset.stock), el.dataset.unit, el.dataset.ref || ''
      );
    });
  });

  // Payment method toggle
  document.getElementById('metodoPago').addEventListener('change', function() {
    document.getElementById('montoRecibidoGroup').style.display =
      this.value === 'EFECTIVO' ? '' : 'none';
  });

  document.getElementById('montoRecibido').addEventListener('input', updateCambio);

  // Client name sync
  document.getElementById('clienteSelect').addEventListener('change', function() {
    var opt = this.options[this.selectedIndex];
    document.getElementById('clienteNombre').value = opt.dataset.nombre || opt.text || 'Consumidor Final';
  });

  // Form submit
  document.getElementById('saleForm').addEventListener('submit', function(e) {
    if (cart.length === 0) { e.preventDefault(); return; }
    document.getElementById('itemsJson').value = JSON.stringify(cart);
    localStorage.removeItem('techstock_pos_draft');
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.key === 'F1') { e.preventDefault(); document.getElementById('productSearch').focus(); }
    if (e.key === 'F2') { e.preventDefault(); document.getElementById('btnPagar').click(); }
    if (e.key === 'F4') { e.preventDefault(); clearCart(); }
  });
});
