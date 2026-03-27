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
      precio_unitario: price, precio_costo: cost,
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

function clearCart() { cart.length = 0; renderCart(); }

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
    html += '<div class="cart-item" data-idx="' + idx + '">' +
      '<div class="qty-control">' +
        '<button class="btn btn-sm btn-outline-secondary" data-action="qty-down">-</button>' +
        '<input type="number" value="' + item.cantidad + '" min="1" max="' + item.stock + '" step="1" data-action="qty-input">' +
        '<button class="btn btn-sm btn-outline-secondary" data-action="qty-up">+</button>' +
      '</div>' +
      '<div class="item-info">' +
        '<div class="item-name">' + _escapeHtml(item.nombre) + '</div>' +
        '<div class="item-price-edit">' +
          '<input type="number" class="form-control form-control-sm price-input" ' +
                 'value="' + item.precio_unitario + '" min="0" step="100" ' +
                 'data-action="price-input" title="Editar precio">' +
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
}

function updateCambio() {
  var total = cart.reduce(function(s, i) { return s + i.cantidad * i.precio_unitario; }, 0);
  var recibido = parseFloat(document.getElementById('montoRecibido').value) || 0;
  var cambio = Math.max(0, recibido - total);
  document.getElementById('cambioDisplay').textContent = formatMoney(cambio);
}

// ── Event Listeners (initialized on DOMContentLoaded) ──
document.addEventListener('DOMContentLoaded', function() {
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
    document.getElementById('clienteNombre').value = opt.text || 'Consumidor Final';
  });

  // Form submit
  document.getElementById('saleForm').addEventListener('submit', function(e) {
    if (cart.length === 0) { e.preventDefault(); return; }
    document.getElementById('itemsJson').value = JSON.stringify(cart);
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.key === 'F1') { e.preventDefault(); document.getElementById('productSearch').focus(); }
    if (e.key === 'F2') { e.preventDefault(); document.getElementById('btnPagar').click(); }
    if (e.key === 'F4') { e.preventDefault(); clearCart(); }
  });
});
