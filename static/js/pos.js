/**
 * TechStock — Punto de Venta (POS)
 * Cart management, product search, payment handling.
 */
const cart = [];
const formatter = new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP',
  minimumFractionDigits: 0, maximumFractionDigits: 0
});

function formatMoney(v) { return formatter.format(v); }

function addToCart(id, code, name, price, stock, unit) {
  const existing = cart.find(i => i.producto_id === id);
  if (existing) {
    if (existing.cantidad >= stock) { alert('Stock insuficiente'); return; }
    existing.cantidad++;
  } else {
    cart.push({
      producto_id: id, codigo: code, nombre: name,
      precio_unitario: price, cantidad: 1, stock: stock, descuento: 0
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

function clearCart() { cart.length = 0; renderCart(); }

function renderCart() {
  const container = document.getElementById('cartItems');
  const btn = document.getElementById('btnPagar');

  if (cart.length === 0) {
    container.innerHTML = '<div class="text-center text-muted py-4" id="emptyCart">' +
      '<i class="bi bi-cart-x" style="font-size:2rem"></i>' +
      '<p class="mt-2 mb-0">Carrito vacío</p></div>';
    document.getElementById('cartTotal').textContent = '$0';
    btn.disabled = true;
    return;
  }

  btn.disabled = false;
  let html = '';
  let total = 0;
  cart.forEach(function(item, idx) {
    const sub = item.cantidad * item.precio_unitario;
    total += sub;
    html += '<div class="cart-item">' +
      '<div class="qty-control">' +
        '<button class="btn btn-sm btn-outline-secondary" onclick="updateQty(' + idx + ',-1)">-</button>' +
        '<input type="number" value="' + item.cantidad + '" min="1" max="' + item.stock + '" step="1" ' +
               'onchange="setQty(' + idx + ',this.value)">' +
        '<button class="btn btn-sm btn-outline-secondary" onclick="updateQty(' + idx + ',1)">+</button>' +
      '</div>' +
      '<div class="item-info">' +
        '<div class="item-name">' + item.nombre + '</div>' +
        '<div class="item-price">' + formatMoney(item.precio_unitario) + '</div>' +
      '</div>' +
      '<div class="item-subtotal">' + formatMoney(sub) + '</div>' +
      '<button class="remove-btn" onclick="removeFromCart(' + idx + ')"><i class="bi bi-x-lg"></i></button>' +
    '</div>';
  });
  container.innerHTML = html;
  document.getElementById('cartTotal').textContent = formatMoney(total);
  updateCambio();
}

function updateCambio() {
  const total = cart.reduce(function(s, i) { return s + i.cantidad * i.precio_unitario; }, 0);
  const recibido = parseFloat(document.getElementById('montoRecibido').value) || 0;
  const cambio = Math.max(0, recibido - total);
  document.getElementById('cambioDisplay').textContent = formatMoney(cambio);
}

// ── Event Listeners (initialized on DOMContentLoaded) ──
document.addEventListener('DOMContentLoaded', function() {
  // Product search filter
  document.getElementById('productSearch').addEventListener('input', function() {
    var q = this.value.toLowerCase();
    document.querySelectorAll('.product-item').forEach(function(el) {
      var name = el.dataset.name.toLowerCase();
      var code = el.dataset.code.toLowerCase();
      el.style.display = (name.includes(q) || code.includes(q)) ? '' : 'none';
    });
  });

  // Click to add product
  document.querySelectorAll('.product-item').forEach(function(el) {
    el.addEventListener('click', function() {
      addToCart(
        parseInt(el.dataset.id), el.dataset.code, el.dataset.name,
        parseFloat(el.dataset.price), parseFloat(el.dataset.stock), el.dataset.unit
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
