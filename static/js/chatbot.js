// ═══════════════════════════════════════════════════════════════════
// TechStock — Asistente de Ayuda Interactivo (IA + offline)
// ═══════════════════════════════════════════════════════════════════

(function () {
  'use strict';

  // ── Base de conocimiento ──────────────────────────────────────
  var helpData = {
    categorias: [
      {
        id: 'productos',
        icon: 'bi-box-seam',
        titulo: 'Productos e Inventario',
        preguntas: [
          {
            pregunta: 'Como crear un nuevo producto?',
            respuesta: 'Ve a <strong>Inventario > Productos</strong> y haz clic en <strong>"Nuevo Producto"</strong>. Completa los campos obligatorios: codigo (unico por local), nombre, precio de costo y precio de venta. Opcionalmente selecciona categoria, proveedor, stock minimo y unidad de medida. Al guardar, el producto quedara disponible en el POS y en movimientos de inventario.',
            link: '/productos/nuevo'
          },
          {
            pregunta: 'Como registrar una entrada de inventario?',
            respuesta: 'Ve a <strong>Compras > Registrar Entrada</strong>. Selecciona el producto de la lista, ingresa la cantidad que llego y opcionalmente el proveedor. El sistema actualizara automaticamente el stock actual del producto y registrara el movimiento en el historial.',
            link: '/inventario/entrada'
          },
          {
            pregunta: 'Como registrar una salida de inventario?',
            respuesta: 'Ve a <strong>Inventario > Movimientos</strong> y selecciona la opcion de <strong>salida de stock</strong>. Elige el producto, indica la cantidad a retirar y el motivo. El stock se reducira automaticamente. Las ventas desde el POS tambien generan salidas automaticas.',
            link: '/inventario/salida'
          },
          {
            pregunta: 'Como hacer un ajuste de inventario?',
            respuesta: 'El ajuste de inventario permite corregir el stock cuando hay diferencias entre el conteo fisico y el sistema. Ve a <strong>Inventario > Movimientos</strong> y realiza un ajuste indicando el stock real del producto. El sistema registrara la diferencia como movimiento de tipo AJUSTE.',
            link: '/inventario/ajuste'
          },
          {
            pregunta: 'Que son las alertas de stock minimo?',
            respuesta: 'Al crear un producto puedes configurar un <strong>stock minimo</strong>. Cuando el stock actual cae por debajo de ese limite, el producto aparece en el reporte de <strong>"Stock Bajo"</strong> en la seccion de Reportes y tambien se muestra un indicador en el Dashboard.',
            link: '/reportes/stock'
          },
          {
            pregunta: 'Como importar productos desde Excel?',
            respuesta: 'Ve a <strong>Administracion > Importar Excel</strong>. Descarga la plantilla de ejemplo, completa los datos de tus productos (codigo, nombre, precios, stock, etc.) y sube el archivo. El sistema validara cada fila y creara los productos que no existan. Los codigos duplicados se ignoran.',
            link: '/importar'
          },
          {
            pregunta: 'Que unidades de medida estan disponibles?',
            respuesta: 'TechStock soporta las unidades mas comunes: <strong>Unidad, Caja, Par, Kg, Litro, Metro</strong>, entre otras. La unidad se selecciona al crear o editar un producto y aparece en reportes y movimientos de inventario.'
          }
        ]
      },
      {
        id: 'ventas',
        icon: 'bi-cart-check',
        titulo: 'Ventas y POS',
        preguntas: [
          {
            pregunta: 'Como realizar una venta?',
            respuesta: 'Ve a <strong>Ventas > Punto de Venta</strong>. Busca productos por nombre, codigo o referencia. Haz clic en el producto para agregarlo al carrito. Ajusta cantidades si es necesario, selecciona el cliente (opcional), metodo de pago, ingresa el monto recibido y haz clic en <strong>"Completar Venta"</strong>. Se generara un numero de venta automatico.',
            link: '/ventas/pos'
          },
          {
            pregunta: 'Como aplicar descuentos en el POS?',
            respuesta: 'En el Punto de Venta, despues de agregar productos al carrito, puedes ingresar un <strong>descuento por item</strong> haciendo clic en el campo de descuento junto a cada producto. El descuento se aplica como valor fijo y se resta del subtotal de ese item.'
          },
          {
            pregunta: 'Se puede editar el precio de venta en el POS?',
            respuesta: 'Si. En el Punto de Venta puedes hacer clic en el <strong>precio unitario</strong> de cualquier producto del carrito para modificarlo manualmente. Esto es util para precios especiales o negociados. El precio manual solo aplica a esa venta y no modifica el precio base del producto.'
          },
          {
            pregunta: 'Como anular una venta?',
            respuesta: 'Ve a <strong>Ventas > Historial de Ventas</strong>, busca la venta que deseas anular y abre su detalle. Haz clic en <strong>"Anular Venta"</strong>. El stock de los productos se revertira automaticamente y la venta quedara marcada como ANULADA. Esta accion queda registrada en la auditoria.',
            link: '/ventas'
          },
          {
            pregunta: 'Como ver el historial de ventas?',
            respuesta: 'Ve a <strong>Ventas > Historial Ventas</strong>. Veras todas las ventas registradas con su numero, fecha, cliente, total y estado. Puedes filtrar por fecha y buscar por numero de venta. Haz clic en una venta para ver su detalle completo.',
            link: '/ventas'
          },
          {
            pregunta: 'Que metodos de pago acepta el POS?',
            respuesta: 'El POS acepta <strong>Efectivo, Tarjeta, Transferencia y Credito</strong>. Al seleccionar Efectivo, puedes ingresar el monto recibido y el sistema calcula automaticamente el cambio. Los demas metodos registran el pago completo.'
          }
        ]
      },
      {
        id: 'finanzas',
        icon: 'bi-cash-coin',
        titulo: 'Finanzas (Deudas/Facturas)',
        preguntas: [
          {
            pregunta: 'Como registrar una deuda (cuenta por pagar)?',
            respuesta: 'Ve a <strong>Finanzas > Cuentas por Pagar</strong> y haz clic en <strong>"Nueva Deuda"</strong>. Ingresa el concepto, monto total, acreedor (proveedor, banco, persona u otro) y fecha de vencimiento. La deuda se crea con estado PENDIENTE.',
            link: '/deudas/nueva'
          },
          {
            pregunta: 'Como registrar una factura (cuenta por cobrar)?',
            respuesta: 'Ve a <strong>Finanzas > Cuentas por Cobrar</strong> y haz clic en <strong>"Nueva Factura"</strong>. Ingresa el numero de factura, cliente, concepto, monto total y fecha de vencimiento. La factura se crea con estado PENDIENTE.',
            link: '/facturas/nueva'
          },
          {
            pregunta: 'Como registrar pagos parciales?',
            respuesta: 'Tanto en deudas como en facturas, abre el <strong>detalle</strong> del registro y haz clic en <strong>"Registrar Pago"</strong> (o "Registrar Cobro" para facturas). Ingresa el monto parcial, metodo de pago y comprobante opcional. El estado cambiara a PARCIAL automaticamente. Cuando el total pagado iguale al monto, pasara a PAGADO/COBRADO.',
          },
          {
            pregunta: 'Como ver deudas vencidas?',
            respuesta: 'En <strong>Reportes > Reporte Deudas</strong> puedes ver un resumen de todas las deudas agrupadas por estado. Las deudas vencidas se resaltan automaticamente cuando la fecha de vencimiento ya paso y aun tienen saldo pendiente.',
            link: '/deudas/reporte'
          },
          {
            pregunta: 'Como importar facturas desde Excel?',
            respuesta: 'Ve a <strong>Administracion > Importar Excel</strong> y selecciona la opcion de <strong>Facturas</strong>. Descarga la plantilla, completa los datos (numero, cliente, monto, fecha) y sube el archivo. El sistema creara las facturas automaticamente.',
            link: '/importar'
          },
          {
            pregunta: 'Como registrar y categorizar gastos?',
            respuesta: 'Ve a <strong>Finanzas > Gastos</strong> y haz clic en <strong>"Nuevo Gasto"</strong>. Ingresa el concepto, monto, categoria (Arriendo, Servicios, Nomina, etc.), tipo (Directo o Indirecto) y metodo de pago. Puedes filtrar gastos por categoria y rango de fechas.',
            link: '/gastos'
          }
        ]
      },
      {
        id: 'clientes',
        icon: 'bi-people',
        titulo: 'Clientes y Proveedores',
        preguntas: [
          {
            pregunta: 'Como crear un nuevo cliente?',
            respuesta: 'Ve a <strong>Ventas > Clientes</strong> y haz clic en <strong>"Nuevo Cliente"</strong>. Ingresa nombre, tipo de documento, numero de documento, telefono, email y direccion. El cliente quedara disponible para asignarlo en ventas.',
            link: '/clientes/nuevo'
          },
          {
            pregunta: 'Como ver el historial de compras de un cliente?',
            respuesta: 'Ve a <strong>Ventas > Clientes</strong> y haz clic en el nombre del cliente para abrir su <strong>detalle</strong>. Alli veras todas sus ventas asociadas, el total comprado y las facturas pendientes si las tiene.',
            link: '/clientes'
          },
          {
            pregunta: 'Como crear un nuevo proveedor?',
            respuesta: 'Ve a <strong>Compras > Proveedores</strong> y haz clic en <strong>"Nuevo Proveedor"</strong>. Ingresa nombre, contacto, telefono, email, direccion y NIT/RUC. El proveedor quedara disponible para asignarlo a productos y entradas de inventario.',
            link: '/proveedores/nuevo'
          },
          {
            pregunta: 'Como ver las deudas con un proveedor?',
            respuesta: 'Ve a <strong>Compras > Proveedores</strong> y haz clic en el nombre del proveedor para abrir su <strong>detalle</strong>. Alli veras las deudas asociadas a ese proveedor, el total adeudado y el historial de pagos.',
            link: '/proveedores'
          },
          {
            pregunta: 'Se pueden desactivar clientes o proveedores?',
            respuesta: 'Si. TechStock usa <strong>eliminacion suave</strong> (soft delete). Al eliminar un cliente o proveedor, este se desactiva y deja de aparecer en las listas de seleccion, pero su historial se conserva intacto para consultas y reportes.'
          },
          {
            pregunta: 'Que son los acreedores?',
            respuesta: 'Los acreedores son entidades a las que tu negocio les debe dinero. Pueden ser de tipo <strong>Proveedor, Banco, Persona u Otro</strong>. Se usan al registrar deudas para vincular a quien se le debe. Ve a <strong>Finanzas > Acreedores</strong> para gestionarlos.',
            link: '/acreedores'
          }
        ]
      },
      {
        id: 'reportes',
        icon: 'bi-bar-chart-line',
        titulo: 'Reportes y Dashboard',
        preguntas: [
          {
            pregunta: 'Que muestra el Dashboard?',
            respuesta: 'El Dashboard es la pantalla principal con un resumen del estado del negocio: <strong>productos activos, valor del inventario, ventas del periodo, ganancias, deudas y facturas pendientes</strong>. Incluye 7 graficas: ventas por dia, por metodo de pago, top productos, categorias y mas.',
            link: '/'
          },
          {
            pregunta: 'Como filtrar por rango de fechas?',
            respuesta: 'En el Dashboard veras selectores de <strong>fecha desde</strong> y <strong>fecha hasta</strong> en la parte superior. Al cambiar las fechas, todas las metricas y graficas se recalculan para mostrar solo la informacion del periodo seleccionado.'
          },
          {
            pregunta: 'Como exportar datos a Excel?',
            respuesta: 'En los reportes de <strong>Stock Actual y Movimientos</strong> encontraras un boton <strong>"Exportar Excel"</strong>. Tambien puedes exportar la lista de productos desde la vista de productos. El archivo se descarga automaticamente como .xlsx.',
            link: '/reportes/stock'
          },
          {
            pregunta: 'Donde veo el reporte de stock bajo?',
            respuesta: 'Ve a <strong>Reportes > Stock Actual</strong>. Los productos con stock por debajo del minimo configurado se resaltan en rojo. Tambien puedes filtrar para mostrar solo productos con stock bajo.',
            link: '/reportes/stock'
          },
          {
            pregunta: 'Como ver los movimientos de inventario?',
            respuesta: 'Ve a <strong>Reportes > Movimientos</strong> para ver el historial completo de entradas, salidas y ajustes. Puedes filtrar por producto, tipo de movimiento y rango de fechas.',
            link: '/reportes/movimientos'
          },
          {
            pregunta: 'Como ver reportes financieros?',
            respuesta: 'Los reportes financieros estan en la seccion <strong>Reportes</strong>: <strong>Reporte de Deudas</strong> (cuentas por pagar agrupadas por estado y vencimiento) y <strong>Reporte de Facturas</strong> (cuentas por cobrar con resumen de cobros). Ambos se pueden exportar a Excel.',
            link: '/deudas/reporte'
          }
        ]
      },
      {
        id: 'configuracion',
        icon: 'bi-gear',
        titulo: 'Configuracion',
        preguntas: [
          {
            pregunta: 'Como cambiar el nombre del negocio?',
            respuesta: 'Ve a <strong>Administracion > Configuracion</strong>. En el campo <strong>"Nombre del Negocio"</strong> escribe el nuevo nombre. Este se mostrara en los recibos de venta y en los reportes PDF. Haz clic en Guardar para aplicar los cambios.',
            link: '/configuracion'
          },
          {
            pregunta: 'Como configurar la moneda?',
            respuesta: 'En <strong>Administracion > Configuracion</strong> puedes cambiar el <strong>simbolo de moneda</strong> (ej: $, S/., Bs.) y el <strong>codigo de moneda</strong> (ej: COP, USD, PEN). Esto afecta como se muestran los valores monetarios en toda la aplicacion.',
            link: '/configuracion'
          },
          {
            pregunta: 'Como personalizar el recibo de venta?',
            respuesta: 'En <strong>Administracion > Configuracion</strong> encontraras los campos <strong>"Mensaje del Recibo"</strong> y <strong>"Pie de Factura"</strong>. Aqui puedes escribir mensajes personalizados que apareceran al final de cada recibo impreso, como un agradecimiento o politicas de devolucion.',
            link: '/configuracion'
          },
          {
            pregunta: 'Como configurar NIT y direccion del negocio?',
            respuesta: 'En <strong>Administracion > Configuracion</strong> puedes ingresar el <strong>NIT</strong>, <strong>direccion</strong>, <strong>telefono</strong> y <strong>email</strong> del negocio. Esta informacion aparece en los encabezados de facturas y recibos.',
            link: '/configuracion'
          },
          {
            pregunta: 'La configuracion es por local?',
            respuesta: 'Si. Cada local tiene su <strong>propia configuracion</strong> independiente. Si eres SUPERADMIN, primero selecciona el local que deseas configurar usando el selector en la barra superior, y luego ve a Configuracion para modificar los datos de ese local.'
          }
        ]
      },
      {
        id: 'usuarios',
        icon: 'bi-person-lock',
        titulo: 'Usuarios y Permisos',
        preguntas: [
          {
            pregunta: 'Que roles existen en TechStock?',
            respuesta: 'Hay 4 roles:<br><strong>SUPERADMIN</strong> — Gestion global de todos los locales<br><strong>ADMIN</strong> — Acceso total dentro de su local<br><strong>VENDEDOR</strong> — Dashboard, productos, ventas, clientes, caja, finanzas, reportes<br><strong>BODEGUERO</strong> — Dashboard, productos, categorias, inventario, proveedores, reportes'
          },
          {
            pregunta: 'Como crear un nuevo usuario?',
            respuesta: 'Ve a <strong>Administracion > Usuarios</strong> y haz clic en <strong>"Nuevo Usuario"</strong>. Ingresa nombre de usuario, contrasena, nombre completo, selecciona el rol y el local al que pertenecera. Los permisos se asignan automaticamente segun el rol, pero puedes personalizarlos.',
            link: '/usuarios/nuevo'
          },
          {
            pregunta: 'Como personalizar los permisos de un usuario?',
            respuesta: 'Al crear o editar un usuario, debajo de la seleccion de rol veras la lista de <strong>modulos disponibles</strong>. Puedes marcar o desmarcar modulos especificos para crear una combinacion personalizada de permisos, diferente a los que el rol asigna por defecto.'
          },
          {
            pregunta: 'Como cambiar mi contrasena?',
            respuesta: 'Haz clic en tu nombre de usuario en la esquina superior derecha y selecciona <strong>"Mi Perfil"</strong>. Alli encontraras la opcion para cambiar tu contrasena. Debes ingresar la contrasena actual y la nueva contrasena dos veces para confirmar.',
            link: '/perfil'
          },
          {
            pregunta: 'Se puede desactivar un usuario sin eliminarlo?',
            respuesta: 'Si. Al <strong>eliminar</strong> un usuario desde la lista de usuarios, el sistema lo <strong>desactiva</strong> (soft delete). El usuario ya no podra iniciar sesion pero su historial de ventas y auditoria se conserva. Un administrador puede reactivarlo posteriormente.'
          },
          {
            pregunta: 'Como funciona el multi-cuenta?',
            respuesta: 'TechStock permite tener <strong>varias sesiones guardadas</strong> en el mismo navegador. En la pantalla de login, puedes agregar cuentas adicionales con <strong>"Agregar Cuenta"</strong>. Luego puedes alternar entre cuentas sin necesidad de escribir la contrasena cada vez.'
          }
        ]
      },
      {
        id: 'backup',
        icon: 'bi-shield-check',
        titulo: 'Backup y Datos',
        preguntas: [
          {
            pregunta: 'Como hacer un backup de la base de datos?',
            respuesta: 'Ve a <strong>Administracion > Backups</strong> y haz clic en <strong>"Crear Backup"</strong>. El sistema generara un archivo de respaldo con todos los datos del sistema. Descargalo y guardalo en un lugar seguro. Se recomienda hacer backups regularmente.',
            link: '/backup'
          },
          {
            pregunta: 'Como restaurar un backup?',
            respuesta: 'Ve a <strong>Administracion > Backups</strong> y usa la opcion <strong>"Restaurar Backup"</strong>. Selecciona el archivo de backup previamente descargado. <strong>Atencion:</strong> La restauracion reemplazara TODOS los datos actuales con los del backup.',
            link: '/backup'
          },
          {
            pregunta: 'Que datos incluye el backup?',
            respuesta: 'El backup incluye <strong>todos los datos del sistema</strong>: locales, usuarios, productos, categorias, proveedores, clientes, ventas, movimientos de inventario, caja, deudas, facturas, gastos, acreedores, configuracion y registros de auditoria.'
          },
          {
            pregunta: 'Como importar datos desde Excel?',
            respuesta: 'Ve a <strong>Administracion > Importar Excel</strong>. Puedes importar <strong>categorias, productos y facturas</strong> desde archivos Excel. Descarga la plantilla de ejemplo para cada tipo, completa los datos y sube el archivo. El sistema valida cada fila antes de importar.',
            link: '/importar'
          },
          {
            pregunta: 'Cada cuanto deberia hacer backup?',
            respuesta: 'Se recomienda hacer backup <strong>al menos una vez al dia</strong> si hay actividad de ventas frecuente, o <strong>semanalmente</strong> si el volumen es bajo. Siempre haz backup <strong>antes de restaurar otro backup</strong> o antes de cambios importantes en la configuracion.'
          },
          {
            pregunta: 'Solo el SUPERADMIN puede hacer backups?',
            respuesta: 'Si. Solo el usuario con rol <strong>SUPERADMIN</strong> tiene acceso al modulo de backups. Esto es por seguridad, ya que los backups contienen toda la informacion del sistema incluyendo datos de todos los locales.'
          }
        ]
      },
      {
        id: 'caja',
        icon: 'bi-cash-stack',
        titulo: 'Caja',
        preguntas: [
          {
            pregunta: 'Como abrir caja?',
            respuesta: 'Ve a <strong>Ventas > Caja</strong> y haz clic en <strong>"Abrir Caja"</strong>. Ingresa el monto de apertura (dinero fisico con el que inicias). Solo puede haber una caja abierta a la vez por usuario. Debes tener caja abierta para registrar ventas.',
            link: '/caja'
          },
          {
            pregunta: 'Como cerrar caja?',
            respuesta: 'Ve a <strong>Ventas > Caja</strong> y haz clic en <strong>"Cerrar Caja"</strong>. Ingresa el monto real contado en la caja. El sistema comparara con el monto esperado (apertura + ventas - egresos) y mostrara la diferencia si la hay.',
            link: '/caja'
          },
          {
            pregunta: 'Que son los movimientos de caja?',
            respuesta: 'Los movimientos de caja registran todo el dinero que entra y sale: <strong>ingresos</strong> (ventas en efectivo, aportes) y <strong>egresos</strong> (retiros, gastos). Las ventas se registran automaticamente como ingreso al completarlas.'
          },
          {
            pregunta: 'Como ver el historial de cajas?',
            respuesta: 'Ve a <strong>Ventas > Caja</strong> y haz clic en <strong>"Historial"</strong>. Veras todas las cajas cerradas con su fecha, monto de apertura, cierre esperado, cierre real y diferencia.',
            link: '/caja'
          },
          {
            pregunta: 'Puedo hacer ventas sin abrir caja?',
            respuesta: 'No es obligatorio tener caja abierta para registrar una venta, pero es <strong>altamente recomendado</strong> para llevar control del efectivo. Las ventas sin caja abierta no se asocian a ningun cierre de caja.'
          }
        ]
      },
      {
        id: 'auditoria',
        icon: 'bi-clock-history',
        titulo: 'Auditoria y Seguridad',
        preguntas: [
          {
            pregunta: 'Que es el registro de actividad?',
            respuesta: 'El <strong>Registro de Actividad</strong> (auditoria) almacena automaticamente todas las acciones importantes realizadas en el sistema: crear, editar y eliminar productos, ventas, deudas, usuarios, etc. Incluye quien lo hizo, cuando y desde que IP.',
            link: '/auditoria'
          },
          {
            pregunta: 'Como filtrar los registros de auditoria?',
            respuesta: 'En <strong>Administracion > Registro de Actividad</strong> puedes filtrar por <strong>usuario, tipo de accion</strong> (crear, editar, eliminar), <strong>entidad</strong> (producto, venta, etc.) y <strong>rango de fechas</strong>.',
            link: '/auditoria'
          },
          {
            pregunta: 'Se pueden borrar los registros de auditoria?',
            respuesta: '<strong>No.</strong> Los registros de auditoria son permanentes y no se pueden eliminar ni modificar. Esto garantiza la trazabilidad completa de todas las operaciones del sistema.'
          },
          {
            pregunta: 'El sistema es seguro?',
            respuesta: 'TechStock implementa multiples capas de seguridad: <strong>contrasenas hasheadas con bcrypt</strong>, <strong>cookies firmadas con expiracion</strong>, <strong>proteccion CSRF en todos los formularios</strong>, <strong>control de acceso por roles y permisos</strong>, y <strong>aislamiento multi-tenant</strong> por local.'
          },
          {
            pregunta: 'Que es el multi-tenant?',
            respuesta: 'Multi-tenant significa que un solo sistema atiende <strong>multiples locales o sucursales</strong>. Cada local tiene sus propios datos (productos, ventas, inventario, etc.) completamente aislados. Un SUPERADMIN puede gestionar todos los locales desde un unico panel.'
          }
        ]
      }
    ]
  };

  // ── Estado del chatbot ────────────────────────────────────────
  var estado = {
    abierto: false,
    historial: [],       // Mensajes mostrados [{tipo:'bot'|'user', html:'...'}]
    categoriaActual: null, // id de categoria para "volver"
    iaDisponible: false,   // true si el backend tiene Gemini configurado
    historialIA: [],       // Historial para contexto de IA [{role:'user'|'assistant', content:'...'}]
    cargandoIA: false      // true mientras espera respuesta de la IA
  };

  // ── Elementos DOM ─────────────────────────────────────────────
  var botonFlotante, panelChat, areaMsg, inputBusqueda, btnEnviar, btnCerrar;

  // ── Inicializacion ────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    botonFlotante = document.getElementById('chatbotToggle');
    panelChat     = document.getElementById('chatbotPanel');
    areaMsg       = document.getElementById('chatbotMensajes');
    inputBusqueda = document.getElementById('chatbotInput');
    btnEnviar     = document.getElementById('chatbotEnviar');
    btnCerrar     = document.getElementById('chatbotCerrar');

    if (!botonFlotante || !panelChat) return;

    // Restaurar estado desde sessionStorage
    var guardado = sessionStorage.getItem('techstock_chatbot_abierto');
    if (guardado === 'true') {
      abrirChat(true);
    }

    // Eventos
    botonFlotante.addEventListener('click', function () {
      if (estado.abierto) {
        cerrarChat();
      } else {
        abrirChat(false);
      }
    });

    btnCerrar.addEventListener('click', function () {
      cerrarChat();
    });

    btnEnviar.addEventListener('click', function () {
      ejecutarBusqueda();
    });

    inputBusqueda.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        ejecutarBusqueda();
      }
    });

    // Delegacion de clicks en area de mensajes
    areaMsg.addEventListener('click', function (e) {
      var target = e.target.closest('[data-chatbot-accion]');
      if (!target) return;

      var accion = target.getAttribute('data-chatbot-accion');
      var valor  = target.getAttribute('data-chatbot-valor');

      if (accion === 'categoria') {
        mostrarCategoria(valor);
      } else if (accion === 'pregunta') {
        mostrarRespuesta(valor);
      } else if (accion === 'menu') {
        mostrarMenuPrincipal();
      } else if (accion === 'volver-categoria') {
        mostrarCategoria(estado.categoriaActual);
      } else if (accion === 'link') {
        window.location.href = valor;
      }
    });

    // Cerrar con Escape (solo si chatbot esta abierto)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && estado.abierto) {
        // No cerrar si el command palette esta abierto
        var palette = document.getElementById('commandPaletteOverlay');
        if (palette && palette.classList.contains('active')) return;
        cerrarChat();
      }
    });
  });

  // ── Abrir / Cerrar ───────────────────────────────────────────
  function abrirChat(silencioso) {
    estado.abierto = true;
    panelChat.classList.add('chatbot-abierto');
    botonFlotante.classList.add('chatbot-toggle-activo');
    sessionStorage.setItem('techstock_chatbot_abierto', 'true');

    // Verificar estado de IA y LUEGO mostrar bienvenida
    verificarEstadoIA(function () {
      if (estado.historial.length === 0) {
        mostrarBienvenida();
      }
    });

    // Focus en input
    setTimeout(function () {
      inputBusqueda.focus();
    }, 300);
  }

  function cerrarChat() {
    estado.abierto = false;
    panelChat.classList.remove('chatbot-abierto');
    botonFlotante.classList.remove('chatbot-toggle-activo');
    sessionStorage.setItem('techstock_chatbot_abierto', 'false');
  }

  // ── Renderizar mensajes ───────────────────────────────────────
  // tipo: 'bot' | 'user' | 'bot-menu' (sin burbuja con borde)
  function agregarMensaje(tipo, html, guardar) {
    if (guardar !== false) {
      estado.historial.push({ tipo: tipo, html: html });
    }

    var div = document.createElement('div');
    var esMenu = tipo === 'bot-menu';
    var tipoBase = esMenu ? 'bot' : tipo;
    div.className = 'chatbot-msg chatbot-msg-' + tipoBase;

    if (tipoBase === 'bot') {
      div.innerHTML = '<div class="chatbot-msg-avatar"><i class="bi bi-robot"></i></div>'
        + '<div class="chatbot-msg-contenido">'
        + '<div class="chatbot-msg-burbuja' + (esMenu ? ' chatbot-burbuja-menu' : '') + '">' + html + '</div>'
        + '</div>';
    } else {
      // Usuario: burbuja directa sin wrapper extra
      div.innerHTML = '<div class="chatbot-msg-burbuja">' + html + '</div>';
    }

    areaMsg.appendChild(div);
    scrollAlFinal();
  }

  function agregarElementoExtra(html) {
    var div = document.createElement('div');
    div.className = 'chatbot-extra';
    div.innerHTML = html;
    areaMsg.appendChild(div);
    scrollAlFinal();
  }

  function limpiarMensajes() {
    areaMsg.innerHTML = '';
    estado.historial = [];
  }

  function scrollAlFinal() {
    setTimeout(function () {
      areaMsg.scrollTop = areaMsg.scrollHeight;
    }, 50);
  }

  // ── Menu principal (bienvenida) ───────────────────────────────
  function mostrarBienvenida() {
    limpiarMensajes();

    var saludo = 'Hola!';
    var hora = new Date().getHours();
    if (hora >= 6 && hora < 12) saludo = 'Buenos dias!';
    else if (hora >= 12 && hora < 18) saludo = 'Buenas tardes!';
    else saludo = 'Buenas noches!';

    var html = '<div class="chatbot-bienvenida">';
    html += '<strong>' + saludo + ' Soy tu asistente de TechStock </strong><br>';
    if (estado.iaDisponible) {
      html += '<span class="chatbot-subtitulo">Puedes escribirme lo que necesites o explorar las categorias de ayuda:</span>';
    } else {
      html += '<span class="chatbot-subtitulo">Selecciona una categoria o escribe tu pregunta:</span>';
    }
    html += '</div>';
    html += renderMenuCategorias();

    agregarMensaje('bot-menu', html);
  }

  function mostrarMenuPrincipal() {
    var html = '<div class="chatbot-bienvenida">';
    html += '<span class="chatbot-subtitulo">Selecciona una categoria:</span>';
    html += '</div>';
    html += renderMenuCategorias();

    agregarMensaje('bot-menu', html);
  }

  function renderMenuCategorias() {
    var html = '<div class="chatbot-categorias">';
    for (var i = 0; i < helpData.categorias.length; i++) {
      var cat = helpData.categorias[i];
      html += '<button class="chatbot-cat-btn" data-chatbot-accion="categoria" data-chatbot-valor="' + cat.id + '">';
      html += '<i class="bi ' + cat.icon + '"></i> ' + cat.titulo;
      html += '</button>';
    }
    html += '</div>';
    return html;
  }

  // ── Mostrar categoria (lista de preguntas) ────────────────────
  function mostrarCategoria(catId) {
    var cat = null;
    for (var i = 0; i < helpData.categorias.length; i++) {
      if (helpData.categorias[i].id === catId) {
        cat = helpData.categorias[i];
        break;
      }
    }
    if (!cat) return;

    estado.categoriaActual = catId;

    // Mensaje del usuario
    agregarMensaje('user', '<i class="bi ' + cat.icon + ' me-1"></i>' + cat.titulo);

    // Respuesta del bot con preguntas
    var html = '<div class="chatbot-preguntas-titulo">';
    html += '<i class="bi ' + cat.icon + ' me-1"></i><strong>' + cat.titulo + '</strong>';
    html += '</div>';
    html += '<div class="chatbot-preguntas-lista">';
    for (var j = 0; j < cat.preguntas.length; j++) {
      html += '<button class="chatbot-pregunta-btn" data-chatbot-accion="pregunta" data-chatbot-valor="' + catId + ':' + j + '">';
      html += '<i class="bi bi-chat-left-text me-2"></i>' + cat.preguntas[j].pregunta;
      html += '</button>';
    }
    html += '</div>';
    html += '<div class="chatbot-nav">';
    html += '<button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-arrow-left me-1"></i>Menu principal</button>';
    html += '</div>';

    agregarMensaje('bot-menu', html);
  }

  // ── Mostrar respuesta a una pregunta ──────────────────────────
  function mostrarRespuesta(valor) {
    var partes = valor.split(':');
    var catId = partes[0];
    var idx = parseInt(partes[1], 10);

    var cat = null;
    for (var i = 0; i < helpData.categorias.length; i++) {
      if (helpData.categorias[i].id === catId) {
        cat = helpData.categorias[i];
        break;
      }
    }
    if (!cat || !cat.preguntas[idx]) return;

    var preg = cat.preguntas[idx];

    // Mensaje del usuario
    agregarMensaje('user', preg.pregunta);

    // Respuesta del bot (texto con burbuja)
    var html = '<div class="chatbot-respuesta">';
    html += '<p>' + preg.respuesta + '</p>';
    if (preg.link) {
      html += '<a href="' + preg.link + '" class="chatbot-link-btn" data-chatbot-accion="link" data-chatbot-valor="' + preg.link + '">';
      html += '<i class="bi bi-arrow-right-circle me-1"></i>Ir a ' + preg.link;
      html += '</a>';
    }
    html += '</div>';
    agregarMensaje('bot', html);

    // Nav como elemento extra fuera de la burbuja
    agregarElementoExtra('<div class="chatbot-nav">'
      + '<button class="chatbot-nav-btn" data-chatbot-accion="volver-categoria"><i class="bi bi-arrow-left me-1"></i>Volver a ' + cat.titulo + '</button>'
      + '<button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-house me-1"></i>Menu principal</button>'
      + '</div>');
  }

  // ── Busqueda (IA o local) ──────────────────────────────────────
  function ejecutarBusqueda() {
    var texto = inputBusqueda.value.trim();
    if (!texto || estado.cargandoIA) return;

    inputBusqueda.value = '';

    // Mensaje del usuario
    agregarMensaje('user', escapeHtml(texto));

    // Si la IA esta disponible, usar IA
    if (estado.iaDisponible) {
      consultarIA(texto);
    } else {
      busquedaLocal(texto);
    }
  }

  // ── Busqueda local (offline) ──────────────────────────────────
  function busquedaLocal(texto) {
    var resultados = buscar(texto);

    if (resultados.length === 0) {
      var html = '<div class="chatbot-sin-resultados">';
      html += '<i class="bi bi-search me-2"></i>No encontre resultados para <strong>"' + escapeHtml(texto) + '"</strong>.';
      html += '<br><span class="chatbot-subtitulo">Intenta con otras palabras o navega por las categorias.</span>';
      html += '</div>';
      agregarMensaje('bot', html);
    } else {
      var html = '<div class="chatbot-resultados-titulo">';
      html += '<i class="bi bi-search me-1"></i>Encontre <strong>' + resultados.length + '</strong> resultado' + (resultados.length > 1 ? 's' : '') + ':';
      html += '</div>';
      html += '<div class="chatbot-preguntas-lista">';
      for (var i = 0; i < resultados.length; i++) {
        var r = resultados[i];
        html += '<button class="chatbot-pregunta-btn" data-chatbot-accion="pregunta" data-chatbot-valor="' + r.catId + ':' + r.idx + '">';
        html += '<span class="chatbot-resultado-cat"><i class="bi ' + r.catIcon + ' me-1"></i>' + r.catTitulo + '</span>';
        html += r.pregunta;
        html += '</button>';
      }
      html += '</div>';
      agregarMensaje('bot-menu', html);
    }

    // Nav siempre fuera de la burbuja
    agregarElementoExtra('<div class="chatbot-nav"><button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-house me-1"></i>Menu principal</button></div>');
  }

  // ── Verificar estado de IA ────────────────────────────────────
  function verificarEstadoIA(callback) {
    fetch('/api/chatbot/status', { credentials: 'same-origin' })
      .then(function (resp) {
        if (!resp.ok) throw new Error('status ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        estado.iaDisponible = data.ai_available === true;
        actualizarIndicadorIA();
        if (callback) callback();
      })
      .catch(function () {
        estado.iaDisponible = false;
        actualizarIndicadorIA();
        if (callback) callback();
      });
  }

  function actualizarIndicadorIA() {
    var dot = document.getElementById('chatbotStatusDot');
    var modoTexto = document.getElementById('chatbotModoTexto');

    if (dot) {
      if (estado.iaDisponible) {
        dot.className = 'chatbot-status-dot online';
      } else {
        dot.className = 'chatbot-status-dot offline';
      }
    }
    if (modoTexto) {
      modoTexto.textContent = estado.iaDisponible ? 'Asistente IA' : 'Ayuda offline';
    }
  }

  // ── Consultar IA ──────────────────────────────────────────────
  function consultarIA(texto) {
    estado.cargandoIA = true;
    btnEnviar.disabled = true;
    inputBusqueda.disabled = true;

    // Mostrar indicador de typing
    var typingId = mostrarTyping();

    // Agregar al historial de contexto
    estado.historialIA.push({ role: 'user', content: texto });

    fetch('/api/chatbot/ask', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: texto,
        history: estado.historialIA.slice(-6)
      })
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('status ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        removerTyping(typingId);

        if (data.source === 'ai' && data.response) {
          // Respuesta de IA exitosa
          var html = '<div class="chatbot-respuesta chatbot-respuesta-ia">';
          html += formatearRespuestaIA(data.response);
          html += '</div>';
          agregarMensaje('bot', html);
          // Badge IA y nav como elementos separados bajo la burbuja
          agregarElementoExtra('<span class="chatbot-ia-badge"><i class="bi bi-stars me-1"></i>Respuesta IA</span>');
          agregarElementoExtra('<div class="chatbot-nav"><button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-house me-1"></i>Menu principal</button></div>');

          // Guardar respuesta en historial de contexto
          estado.historialIA.push({ role: 'assistant', content: data.response });
          // Limitar historial de contexto
          if (estado.historialIA.length > 20) {
            estado.historialIA = estado.historialIA.slice(-12);
          }
        } else if (data.source === 'system' && data.response) {
          // Mensaje del sistema (rate limit, validacion, errores de API)
          var html = '<div class="chatbot-sin-resultados">';
          html += '<i class="bi bi-info-circle me-2"></i>' + escapeHtml(data.response);
          html += '</div>';
          agregarMensaje('bot', html);
          agregarElementoExtra('<div class="chatbot-nav"><button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-house me-1"></i>Menu principal</button></div>');
        } else {
          // Offline — fallback a busqueda local
          busquedaLocal(texto);
        }
      })
      .catch(function (err) {
        removerTyping(typingId);
        // Error de red — mostrar mensaje amigable
        var html = '<div class="chatbot-sin-resultados">';
        html += '<i class="bi bi-wifi-off me-2"></i>No pude conectar con el asistente IA.';
        html += '<br><span class="chatbot-subtitulo">Revisa tu conexion o intenta de nuevo.</span>';
        html += '</div>';
        agregarMensaje('bot', html);
        agregarElementoExtra('<div class="chatbot-nav"><button class="chatbot-nav-btn" data-chatbot-accion="menu"><i class="bi bi-house me-1"></i>Menu principal</button></div>');
      })
      .finally(function () {
        estado.cargandoIA = false;
        btnEnviar.disabled = false;
        inputBusqueda.disabled = false;
        inputBusqueda.focus();
      });
  }

  // ── Indicador de typing (tres puntos animados) ────────────────
  function mostrarTyping() {
    var id = 'typing-' + Date.now();
    var div = document.createElement('div');
    div.className = 'chatbot-msg chatbot-msg-bot';
    div.id = id;
    div.innerHTML = '<div class="chatbot-msg-avatar"><i class="bi bi-robot"></i></div>'
      + '<div class="chatbot-msg-contenido">'
      + '<div class="chatbot-msg-burbuja">'
      + '<div class="chatbot-typing">'
      + '<div class="chatbot-typing-dot"></div>'
      + '<div class="chatbot-typing-dot"></div>'
      + '<div class="chatbot-typing-dot"></div>'
      + '</div></div></div>';
    areaMsg.appendChild(div);
    scrollAlFinal();
    return id;
  }

  function removerTyping(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  // ── Formatear respuesta de IA (sanitizar y convertir markdown basico) ──
  function formatearRespuestaIA(texto) {
    // Escapar HTML primero
    var safe = escapeHtml(texto);
    // Convertir **bold** a <strong>
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Convertir *italic* a <em>
    safe = safe.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Convertir listas con - al inicio de linea
    safe = safe.replace(/^- (.+)$/gm, '<span class="chatbot-list-item">$1</span>');
    // Convertir rutas tipo "Modulo > Submodulo" en negritas
    safe = safe.replace(/(&gt;\s*)/g, ' <i class="bi bi-chevron-right" style="font-size:0.65em;opacity:0.6"></i> ');
    // Convertir saltos de linea dobles en parrafos, simples en <br>
    safe = safe.replace(/\n\n/g, '</p><p>');
    safe = safe.replace(/\n/g, '<br>');
    safe = '<p>' + safe + '</p>';
    return safe;
  }

  function buscar(texto) {
    var terminos = normalizar(texto).split(/\s+/);
    var resultados = [];

    for (var i = 0; i < helpData.categorias.length; i++) {
      var cat = helpData.categorias[i];
      for (var j = 0; j < cat.preguntas.length; j++) {
        var p = cat.preguntas[j];
        var contenido = normalizar(p.pregunta + ' ' + p.respuesta + ' ' + cat.titulo);

        // Todas las palabras deben coincidir
        var coincide = true;
        for (var k = 0; k < terminos.length; k++) {
          if (contenido.indexOf(terminos[k]) === -1) {
            coincide = false;
            break;
          }
        }

        if (coincide) {
          resultados.push({
            catId: cat.id,
            catIcon: cat.icon,
            catTitulo: cat.titulo,
            idx: j,
            pregunta: p.pregunta
          });
        }
      }
    }

    return resultados;
  }

  function normalizar(texto) {
    return texto.toLowerCase()
      .replace(/[áàäâ]/g, 'a')
      .replace(/[éèëê]/g, 'e')
      .replace(/[íìïî]/g, 'i')
      .replace(/[óòöô]/g, 'o')
      .replace(/[úùüû]/g, 'u')
      .replace(/ñ/g, 'n')
      .replace(/<[^>]*>/g, ' ')  // Strip HTML tags
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

})();
