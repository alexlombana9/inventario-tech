/**
 * TechStock v3.1 — Sistema de ayuda contextual
 * Muestra modales con informacion relevante para cada modulo.
 */

const helpContent = {
  dashboard: {
    title: 'Dashboard — Panel Principal',
    body: `
      <p>El Dashboard muestra un resumen en tiempo real de tu negocio:</p>
      <ul>
        <li><strong>Metricas generales:</strong> Total de productos, proveedores, valor del inventario y productos con stock bajo.</li>
        <li><strong>Ventas del periodo:</strong> Total vendido, cantidad de ventas, ganancias y ventas del mes.</li>
        <li><strong>Finanzas:</strong> Deudas pendientes, facturas por cobrar y gastos del periodo.</li>
        <li><strong>Graficas:</strong> 7 graficas interactivas — tendencias de ventas, ganancias, top productos, metodos de pago, movimientos, ventas por categoria y stock bajo.</li>
        <li><strong>Filtro de fechas:</strong> Selecciona un rango de fechas para ajustar las metricas de ventas y ganancias.</li>
        <li><strong>Alertas:</strong> Productos con stock bajo que necesitan reabastecimiento.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-lightbulb me-1"></i>
        Los datos se actualizan cada vez que abres el Dashboard. Usa el filtro de fechas para analizar periodos especificos.
      </div>
    `
  },
  productos: {
    title: 'Productos — Ayuda',
    body: `
      <p>Gestiona tu catalogo de productos:</p>
      <ul>
        <li><strong>Codigo:</strong> Identificador unico del producto (ej: CEL-001). No se puede repetir dentro del mismo local.</li>
        <li><strong>Referencia:</strong> Codigo del fabricante o proveedor (opcional).</li>
        <li><strong>Precio de costo:</strong> Lo que pagas al proveedor.</li>
        <li><strong>Precio de venta:</strong> Lo que cobras al cliente.</li>
        <li><strong>Precio minimo:</strong> El precio mas bajo al que puedes vender (protege tu margen en el POS).</li>
        <li><strong>Stock minimo:</strong> El sistema te alerta cuando el stock llegue a este numero.</li>
        <li><strong>Unidad de medida:</strong> Unidad, Caja, Metro, Kilo, Litro, Par o Rollo.</li>
        <li><strong>Margen:</strong> Se calcula automaticamente: ((Venta - Costo) / Costo) x 100.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-lightbulb me-1"></i>
        Los productos en <span class="text-danger fw-bold">rojo</span> tienen stock bajo. Usa el filtro "Stock Bajo" para verlos. Exporta la lista a Excel con el boton verde.
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
        No puedes eliminar una categoria que tiene productos activos asociados. Primero mueve o desactiva los productos.
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
        <li>En el detalle de un proveedor puedes ver sus ultimos movimientos, productos y deudas pendientes.</li>
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
        <li>Busca productos por nombre, codigo o referencia y agregalos al carrito.</li>
        <li>Ajusta cantidades y aplica descuentos por item.</li>
        <li>Selecciona un cliente registrado o deja como "Consumidor Final".</li>
        <li>Metodos de pago: Efectivo, Tarjeta, Transferencia, Credito o Mixto.</li>
        <li>En pagos en efectivo, el sistema calcula el cambio.</li>
        <li>Al confirmar la venta, el stock se actualiza y se registra en la caja.</li>
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
        <li>Haz clic en una venta para ver el detalle con productos, precios y ganancia por item.</li>
        <li>Los administradores pueden <strong>editar</strong> datos generales de la venta.</li>
        <li>Puedes <strong>anular</strong> una venta si es necesario (devuelve el stock automaticamente).</li>
        <li>Descarga el <strong>recibo en PDF</strong> desde el detalle de cada venta.</li>
        <li>Exporta el historial a <strong>Excel</strong> con los filtros aplicados.</li>
      </ul>
    `
  },
  clientes: {
    title: 'Clientes — Ayuda',
    body: `
      <p>Gestiona la informacion de tus clientes:</p>
      <ul>
        <li>Registra nombre, empresa, documento, telefono, email y direccion.</li>
        <li>Tipos de documento: CC, NIT, CE, Pasaporte.</li>
        <li>Al hacer una venta, puedes seleccionar un cliente registrado.</li>
        <li>Desde el detalle del cliente puedes ver su historial de compras.</li>
        <li>Los clientes con ventas a credito muestran su <strong>saldo pendiente</strong>.</li>
      </ul>
    `
  },
  caja: {
    title: 'Caja Registradora — Ayuda',
    body: `
      <p>Control de efectivo diario:</p>
      <ul>
        <li><strong>Abrir caja:</strong> Ingresa el monto de apertura (efectivo inicial).</li>
        <li><strong>Durante el dia:</strong> Las ventas en efectivo se registran como ingresos automaticamente.</li>
        <li><strong>Movimientos manuales:</strong> Registra egresos por gastos o retiros de efectivo.</li>
        <li><strong>Estado actual:</strong> Ve el saldo esperado en tiempo real (apertura + ingresos - egresos).</li>
        <li><strong>Cerrar caja:</strong> Ingresa el monto real en caja. El sistema calcula la diferencia.</li>
        <li>Si hay sobrante o faltante, se muestra en el cierre.</li>
        <li><strong>Historial:</strong> Consulta todos los cierres anteriores con sus cuadres y detalles.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Es necesario tener la caja abierta para poder registrar ventas. Cada usuario tiene su propia caja.
      </div>
    `
  },
  acreedores: {
    title: 'Acreedores — Ayuda',
    body: `
      <p>Registra las personas o empresas a las que le debes dinero:</p>
      <ul>
        <li><strong>Tipos:</strong> Proveedor, Banco, Persona u Otro.</li>
        <li>Registra nombre, empresa, documento, telefono, email, direccion y notas.</li>
        <li>Las deudas se vinculan automaticamente al acreedor por nombre.</li>
        <li>Un <strong>Proveedor</strong> (modulo Compras) y un <strong>Acreedor</strong> (modulo Finanzas) son conceptos diferentes: el proveedor te vende mercancia, el acreedor es a quien le debes dinero.</li>
        <li>Un proveedor puede ser tambien acreedor si le debes mercancia a credito.</li>
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
        Las deudas en <span class="text-danger fw-bold">rojo</span> estan vencidas y requieren atencion. Consulta el Reporte de Deudas para un resumen consolidado.
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
        <li>Puedes importar facturas desde Excel para cargas masivas.</li>
        <li>Las facturas se pueden anular si fueron creadas por error.</li>
      </ul>
    `
  },
  gastos: {
    title: 'Gastos — Ayuda',
    body: `
      <p>Registra y controla los gastos operativos de tu negocio:</p>
      <ul>
        <li><strong>Tipo:</strong> Directo (relacionado con ventas) o Indirecto (operativo general).</li>
        <li><strong>Categoria:</strong> Arriendo, Servicios publicos, Nomina, Transporte, Insumos, Mantenimiento, etc.</li>
        <li>Registra concepto, monto, fecha, metodo de pago y comprobante.</li>
        <li>Filtra por tipo, categoria y rango de fechas.</li>
        <li>Los gastos se reflejan en el Dashboard como "Gastos del periodo".</li>
        <li>Exporta a Excel para analisis externo.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-lightbulb me-1"></i>
        <strong>Directos:</strong> embalaje, envios. <strong>Indirectos:</strong> arriendo, servicios, nomina.
      </div>
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
      <p class="text-muted small mb-0">Todos los reportes se pueden exportar a Excel para mayor analisis.</p>
    `
  },
  importar: {
    title: 'Importar Excel — Ayuda',
    body: `
      <p>Carga masiva de datos desde archivos Excel:</p>
      <ul>
        <li>Soporta: Categorias, Productos, Clientes, Proveedores, Acreedores, Deudas y Facturas.</li>
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
        <li>Facturas</li>
      </ol>
    `
  },
  usuarios: {
    title: 'Gestion de Usuarios — Ayuda',
    body: `
      <p>Administra las cuentas de acceso:</p>
      <ul>
        <li><strong>Super Administrador:</strong> Gestion global de todos los locales.</li>
        <li><strong>Administrador:</strong> Acceso completo dentro de su local.</li>
        <li><strong>Vendedor:</strong> Ventas, clientes, caja, finanzas y reportes.</li>
        <li><strong>Bodeguero:</strong> Productos, inventario, proveedores y reportes.</li>
      </ul>
      <p class="small">Los permisos se pueden personalizar por usuario. Si se dejan vacios, se usan los del rol.</p>
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
        <li><strong>Logo:</strong> Se muestra en recibos de venta. Cada local puede tener su propio logo.</li>
        <li><strong>Moneda:</strong> Simbolo ($) y codigo (COP, USD, etc.).</li>
        <li><strong>Mensaje de recibo:</strong> Texto al pie del recibo (ej: "Gracias por su compra").</li>
        <li><strong>Pie de factura:</strong> Texto legal al pie de facturas.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        La configuracion es independiente por local. Cada sucursal puede tener su propio nombre, logo y moneda.
      </div>
    `
  },
  backup: {
    title: 'Backups — Ayuda',
    body: `
      <p>Protege tus datos con copias de seguridad:</p>
      <ul>
        <li>Crea un backup con un clic. Se genera una copia completa de toda la base de datos.</li>
        <li>Descarga el archivo y guardalo en un lugar seguro.</li>
        <li>Puedes restaurar un backup previamente descargado si necesitas recuperar datos.</li>
        <li>Se recomienda hacer backup <strong>diariamente</strong>.</li>
        <li>Guarda copias en diferentes lugares (USB, nube, otro equipo).</li>
      </ul>
      <div class="alert alert-warning small py-2 mb-0">
        <i class="bi bi-exclamation-triangle me-1"></i>
        Si el equipo falla y no tienes backup, <strong>los datos se pierden permanentemente</strong>. El backup incluye datos de todos los locales.
      </div>
    `
  },
  perfil: {
    title: 'Mi Perfil — Ayuda',
    body: `
      <p>Gestiona tu informacion personal:</p>
      <ul>
        <li>Cambia tu nombre completo, email y telefono.</li>
        <li>Sube o cambia tu foto de perfil (aparece en la barra superior).</li>
        <li>Cambia tu contrasena (necesitas la contrasena actual, minimo 8 caracteres).</li>
        <li>Tu nombre de usuario y rol solo los puede cambiar un administrador.</li>
        <li>Usa "Agregar Cuenta" en el menu de usuario para iniciar sesion con otro usuario (multi-cuenta).</li>
      </ul>
    `
  },
  auditoria: {
    title: 'Registro de Actividad — Ayuda',
    body: `
      <p>Historial detallado de todas las acciones en el sistema:</p>
      <ul>
        <li>Se registra automaticamente: creacion, edicion, eliminacion, anulacion e inicios de sesion.</li>
        <li>Cada registro incluye: usuario, accion, entidad, detalle, IP y fecha/hora.</li>
        <li>Filtra por <strong>usuario</strong>, <strong>tipo de accion</strong>, <strong>entidad</strong> y <strong>rango de fechas</strong>.</li>
        <li>El registro no se puede editar ni eliminar — es una herramienta de control y transparencia.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Solo los administradores tienen acceso al registro de actividad.
      </div>
    `
  },
  locales: {
    title: 'Gestion de Locales — Ayuda',
    body: `
      <p>Administra multiples sucursales desde una sola instalacion (solo Super Administrador):</p>
      <ul>
        <li>Crea nuevos locales con nombre, codigo unico, direccion y responsable.</li>
        <li>Selecciona un local en la barra superior para operar dentro de el.</li>
        <li>Cada local tiene inventario, ventas, clientes y configuracion independiente.</li>
        <li>Los codigos de producto y numeros de factura son independientes por local.</li>
        <li>El <strong>Super Dashboard</strong> muestra metricas consolidadas de todos los locales.</li>
      </ul>
      <div class="alert alert-info small py-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        Los usuarios normales solo ven datos de su local asignado. El Super Administrador puede ver y operar en todos los locales.
      </div>
    `
  },
  super_dashboard: {
    title: 'Super Dashboard — Ayuda',
    body: `
      <p>Dashboard consolidado para Super Administradores:</p>
      <ul>
        <li>Muestra metricas globales: total locales, usuarios, productos, ventas.</li>
        <li>Tabla comparativa por local con indicadores clave.</li>
        <li>Ventas del dia y del mes por cada local.</li>
        <li>Productos con stock bajo y deudas pendientes por local.</li>
        <li>Haz clic en un local para entrar a su dashboard individual.</li>
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
