/**
 * TechStock — Sistema de ayuda contextual
 * Muestra modales con informacion relevante para cada modulo.
 */

const helpContent = {
  dashboard: {
    title: 'Dashboard — Panel Principal',
    body: `
      <p>El Dashboard muestra un resumen en tiempo real de tu negocio:</p>
      <ul>
        <li><strong>Metricas generales:</strong> Total de productos, proveedores, valor del inventario y productos con stock bajo.</li>
        <li><strong>Ventas del dia:</strong> Total vendido hoy, cantidad de ventas y ventas del mes.</li>
        <li><strong>Finanzas:</strong> Deudas pendientes y facturas por cobrar.</li>
        <li><strong>Graficas:</strong> Tendencias de ventas y movimientos de los ultimos 7 dias.</li>
        <li><strong>Alertas:</strong> Productos con stock bajo que necesitan reabastecimiento.</li>
      </ul>
      <p class="text-muted small mb-0">Los datos se actualizan cada vez que abres el Dashboard.</p>
    `
  },
  productos: {
    title: 'Productos — Ayuda',
    body: `
      <p>Gestiona tu catalogo de productos:</p>
      <ul>
        <li><strong>Codigo:</strong> Identificador unico del producto (ej: CEL-001). No se puede repetir.</li>
        <li><strong>Referencia:</strong> Codigo del fabricante o proveedor (opcional).</li>
        <li><strong>Precio de costo:</strong> Lo que pagas al proveedor.</li>
        <li><strong>Precio de venta:</strong> Lo que cobras al cliente.</li>
        <li><strong>Precio minimo:</strong> El precio mas bajo al que puedes vender (protege tu margen).</li>
        <li><strong>Stock minimo:</strong> El sistema te alerta cuando el stock llegue a este numero.</li>
        <li><strong>Margen:</strong> Se calcula automaticamente: ((Venta - Costo) / Costo) x 100.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-lightbulb me-1"></i>
        Los productos en <span class="text-danger fw-bold">rojo</span> tienen stock bajo. Usa el filtro "Stock Bajo" para verlos.
      </div>
    `
  },
  categorias: {
    title: 'Categorias — Ayuda',
    body: `
      <p>Las categorias te ayudan a organizar tus productos:</p>
      <ul>
        <li>Crea categorias generales (ej: Celulares, Accesorios, Cables).</li>
        <li>Cada producto se asigna a una categoria.</li>
        <li>Los reportes de stock se pueden filtrar por categoria.</li>
        <li>Al importar productos desde Excel, las categorias se crean automaticamente si no existen.</li>
      </ul>
      <div class="alert alert-warning small py-2 mb-0">
        <i class="bi bi-exclamation-triangle me-1"></i>
        No puedes eliminar una categoria que tiene productos asociados.
      </div>
    `
  },
  inventario: {
    title: 'Movimientos de Inventario — Ayuda',
    body: `
      <p>Registra todos los cambios en el stock de tus productos:</p>
      <ul>
        <li><span class="badge bg-success">ENTRADA</span> Recepcion de mercancia: aumenta el stock.</li>
        <li><span class="badge bg-danger">SALIDA</span> Despacho de mercancia: disminuye el stock.</li>
        <li><span class="badge bg-warning text-dark">AJUSTE</span> Correccion de stock: puede aumentar o disminuir.</li>
      </ul>
      <p>Cada movimiento registra: stock anterior, cantidad, stock resultante, proveedor y observaciones.</p>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Los movimientos <strong>no se pueden eliminar</strong>. Si hay un error, usa un Ajuste para corregir.
      </div>
    `
  },
  proveedores: {
    title: 'Proveedores — Ayuda',
    body: `
      <p>Administra la informacion de tus proveedores:</p>
      <ul>
        <li>Registra nombre, contacto, telefono, email, direccion y NIT/RUC.</li>
        <li>Vincula proveedores a productos y entradas de inventario.</li>
        <li>En el detalle de un proveedor puedes ver sus ultimos movimientos y productos.</li>
        <li>Los proveedores desactivados no aparecen en las listas de seleccion.</li>
      </ul>
    `
  },
  ventas: {
    title: 'Punto de Venta — Ayuda',
    body: `
      <p>Registra ventas rapidamente:</p>
      <ul>
        <li><strong>Requisito:</strong> Debes tener la caja abierta para vender.</li>
        <li>Busca productos por nombre o codigo y agregalos al carrito.</li>
        <li>Ajusta cantidades y aplica descuentos por item.</li>
        <li>Metodos de pago: Efectivo, Tarjeta, Transferencia, Credito o Mixto.</li>
        <li>En pagos en efectivo, el sistema calcula el cambio.</li>
        <li>Al confirmar la venta, el stock se actualiza automaticamente.</li>
      </ul>
      <div class="alert alert-warning small py-2 mb-0">
        <i class="bi bi-exclamation-triangle me-1"></i>
        No puedes vender por debajo del <strong>precio minimo</strong> configurado en el producto.
      </div>
    `
  },
  historial_ventas: {
    title: 'Historial de Ventas — Ayuda',
    body: `
      <p>Consulta todas las ventas realizadas:</p>
      <ul>
        <li>Filtra por fecha, metodo de pago o busca por numero de venta.</li>
        <li>Haz clic en una venta para ver el detalle con productos, precios y ganancia.</li>
        <li>Puedes <strong>anular</strong> una venta si es necesario (devuelve el stock).</li>
        <li>Descarga el recibo desde el detalle de cada venta.</li>
      </ul>
    `
  },
  clientes: {
    title: 'Clientes — Ayuda',
    body: `
      <p>Gestiona la informacion de tus clientes:</p>
      <ul>
        <li>Registra nombre, documento, telefono, email y direccion.</li>
        <li>Tipos de documento: CC, NIT, CE, Pasaporte.</li>
        <li>Al hacer una venta, puedes seleccionar un cliente registrado.</li>
        <li>Desde el detalle del cliente puedes ver su historial de compras.</li>
      </ul>
    `
  },
  caja: {
    title: 'Caja Registradora — Ayuda',
    body: `
      <p>Control de efectivo diario:</p>
      <ul>
        <li><strong>Abrir caja:</strong> Ingresa el monto de apertura (efectivo inicial).</li>
        <li><strong>Durante el dia:</strong> Las ventas en efectivo se registran como ingresos.</li>
        <li><strong>Cerrar caja:</strong> Ingresa el monto real en caja. El sistema calcula la diferencia.</li>
        <li>Si hay sobrante o faltante, se muestra en el cierre.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Es necesario tener la caja abierta para poder registrar ventas.
      </div>
    `
  },
  acreedores: {
    title: 'Acreedores — Ayuda',
    body: `
      <p>Registra las personas o empresas a las que le debes dinero:</p>
      <ul>
        <li><strong>Tipos:</strong> Proveedor, Banco, Persona u Otro.</li>
        <li>Registra documento, telefono, email, direccion y notas.</li>
        <li>Las deudas se vinculan automaticamente al acreedor por nombre.</li>
        <li>Un <strong>Proveedor</strong> (modulo Compras) y un <strong>Acreedor</strong> (modulo Finanzas) son conceptos diferentes: el proveedor te vende mercancia, el acreedor es a quien le debes dinero.</li>
      </ul>
    `
  },
  deudas: {
    title: 'Cuentas por Pagar — Ayuda',
    body: `
      <p>Controla lo que debes a terceros:</p>
      <ul>
        <li>Registra concepto, acreedor, monto total y fecha de vencimiento.</li>
        <li>Registra pagos parciales o totales con metodo y comprobante.</li>
        <li><span class="badge badge-pendiente">PENDIENTE</span> Sin pagos realizados.</li>
        <li><span class="badge badge-parcial">PARCIAL</span> Con pagos parciales.</li>
        <li><span class="badge badge-pagado">PAGADO</span> Completamente saldada.</li>
        <li><span class="badge badge-vencido">VENCIDA</span> Paso la fecha limite sin saldar.</li>
      </ul>
      <div class="alert alert-warning small py-2 mb-0">
        <i class="bi bi-exclamation-triangle me-1"></i>
        Las deudas en <span class="text-danger fw-bold">rojo</span> estan vencidas y requieren atencion.
      </div>
    `
  },
  facturas: {
    title: 'Cuentas por Cobrar — Ayuda',
    body: `
      <p>Registra facturas pendientes de cobro:</p>
      <ul>
        <li>El numero de factura se sugiere automaticamente (FAC-0001...).</li>
        <li>Registra datos del cliente, concepto, monto y fecha de vencimiento.</li>
        <li>Registra cobros parciales o totales.</li>
        <li>Los estados son iguales a los de deudas: Pendiente, Parcial, Cobrada, Vencida.</li>
      </ul>
    `
  },
  reportes: {
    title: 'Reportes — Ayuda',
    body: `
      <p>Genera reportes para analizar tu negocio:</p>
      <ul>
        <li><strong>Stock Actual:</strong> Lista completa de productos con stock, precios y valor. Filtra por categoria.</li>
        <li><strong>Movimientos:</strong> Entradas, salidas y ajustes en un rango de fechas.</li>
        <li><strong>Deudas:</strong> Resumen de deudas pendientes, parciales y vencidas.</li>
        <li><strong>Facturas:</strong> Resumen de facturas por cobrar.</li>
      </ul>
      <p class="text-muted small mb-0">Los reportes se pueden exportar a Excel para mayor analisis.</p>
    `
  },
  importar: {
    title: 'Importar Excel — Ayuda',
    body: `
      <p>Carga masiva de datos desde archivos Excel:</p>
      <ul>
        <li>Soporta: Productos, Categorias, Clientes, Proveedores, Acreedores y Deudas.</li>
        <li>Descarga la <strong>plantilla</strong> de cada tipo para ver los encabezados correctos.</li>
        <li>El orden de columnas no importa, el sistema las detecta por nombre.</li>
        <li>Formato aceptado: <code>.xlsx</code> y <code>.xls</code> (maximo 10 MB).</li>
      </ul>
      <p class="fw-semibold">Orden recomendado:</p>
      <ol class="small">
        <li>Categorias</li>
        <li>Proveedores</li>
        <li>Productos</li>
        <li>Clientes</li>
        <li>Acreedores</li>
        <li>Deudas</li>
      </ol>
    `
  },
  usuarios: {
    title: 'Gestion de Usuarios — Ayuda',
    body: `
      <p>Administra las cuentas de acceso:</p>
      <ul>
        <li><strong>Administrador:</strong> Acceso completo a todo el sistema.</li>
        <li><strong>Vendedor:</strong> Ventas, clientes, caja, finanzas y reportes.</li>
        <li><strong>Bodeguero:</strong> Productos, inventario, proveedores y reportes.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Los usuarios desactivados no pueden iniciar sesion pero su historial se conserva.
      </div>
    `
  },
  configuracion: {
    title: 'Configuracion — Ayuda',
    body: `
      <p>Personaliza la informacion de tu negocio:</p>
      <ul>
        <li><strong>Nombre, NIT, direccion, telefono:</strong> Aparecen en recibos y facturas.</li>
        <li><strong>Logo:</strong> Se muestra en recibos de venta.</li>
        <li><strong>Moneda:</strong> Simbolo ($) y codigo (COP, USD, etc.).</li>
        <li><strong>Mensaje de recibo:</strong> Texto al pie del recibo (ej: "Gracias por su compra").</li>
      </ul>
    `
  },
  backup: {
    title: 'Backups — Ayuda',
    body: `
      <p>Protege tus datos con copias de seguridad:</p>
      <ul>
        <li>Crea un backup con un clic. Se genera una copia de toda la base de datos.</li>
        <li>Descarga el archivo y guardalo en un lugar seguro.</li>
        <li>Se recomienda hacer backup <strong>diariamente</strong>.</li>
        <li>Guarda copias en diferentes lugares (USB, nube, otro equipo).</li>
      </ul>
      <div class="alert alert-warning small py-2 mb-0">
        <i class="bi bi-exclamation-triangle me-1"></i>
        Si el equipo falla y no tienes backup, <strong>los datos se pierden</strong>.
      </div>
    `
  },
  perfil: {
    title: 'Mi Perfil — Ayuda',
    body: `
      <p>Gestiona tu informacion personal:</p>
      <ul>
        <li>Cambia tu nombre completo, email y telefono.</li>
        <li>Cambia tu contrasena (necesitas la contrasena actual).</li>
        <li>Tu nombre de usuario y rol solo los puede cambiar un administrador.</li>
        <li>Usa "Cambiar Cuenta" para cerrar sesion e ingresar con otro usuario.</li>
      </ul>
    `
  }
};

// Auto-detect current module from URL and activate help buttons
document.addEventListener('DOMContentLoaded', function() {
  // Handle explicit help trigger buttons (data-help attribute)
  document.querySelectorAll('.btn-help-trigger').forEach(function(btn) {
    btn.addEventListener('click', function() {
      const helpKey = this.getAttribute('data-help');
      showHelp(helpKey);
    });
  });
});

function showHelp(key) {
  const content = helpContent[key];
  if (!content) return;

  const modalLabel = document.getElementById('helpModalLabel');
  const modalBody = document.getElementById('helpModalBody');

  if (modalLabel) modalLabel.innerHTML = '<i class="bi bi-question-circle me-2"></i>' + content.title;
  if (modalBody) modalBody.innerHTML = content.body;

  const modal = new bootstrap.Modal(document.getElementById('helpModal'));
  modal.show();
}
