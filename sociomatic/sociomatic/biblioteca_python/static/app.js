const state = {
  socios: [],
  cuotas: [],
  morosos: [],
  selectedId: null,
  socioCrudId: null,
  config: {},
  tiposSocio: [],
  cobradores: [],
  auditoria: [],
  caja: {
    dia: null,
    movimientos: [],
    resumen: {}
  }
};

const $ = (selector) => document.querySelector(selector);
let adminKeyResolve = null;
let adminKeyReject = null;

function periodoSiguiente() {
  const now = new Date();
  const year = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();
  const month = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  return `${year}-${String(month).padStart(2, '0')}`;
}

function periodoActual() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function fechaActual() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function periodoDefault() {
  return state.config.periodo_default === 'actual' ? periodoActual() : periodoSiguiente();
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });
  const data = await response.json();
  if (!response.ok || data.exito === false) {
    throw new Error(data.error || 'Error de operacion');
  }
  return data;
}

function pedirClaveAdmin(motivo) {
  return Promise.resolve(window.prompt(`${motivo || 'Esta accion requiere permiso.'}\n\nIngrese clave de administrador:`) || '');
}

async function apiAdmin(url, options = {}, motivo = '') {
  const clave = await pedirClaveAdmin(motivo);
  if (!clave) throw new Error('Accion cancelada');
  return api(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-Admin-Key': clave
    }
  });
}

function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 2600);
}

window.addEventListener('unhandledrejection', (event) => {
  const message = event.reason && event.reason.message ? event.reason.message : 'Operacion cancelada';
  if (message !== 'Accion cancelada') toast(message);
  event.preventDefault();
});

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function resetNuevoSocio() {
  const form = $('#formNuevo');
  form.reset();
  form.id.value = '';
  form.nro_socio.value = $('#proximoNroCrud').textContent !== '-' ? $('#proximoNroCrud').textContent : '';
  form.fecha_alta.value = fechaActual();
  form.estado.value = state.config.socio_estado_default || 'activo';
  form.cobrador.value = state.config.socio_cobrador_default || '1';
  state.socioCrudId = null;
  $('#socioFormTitulo').textContent = 'Nuevo socio';
}

async function cargarConfig() {
  const data = await api('/api/config');
  state.config = data.config;
  state.tiposSocio = data.config.tipos_socio || [];
  state.cobradores = data.config.cobradores || [];
  state.auditoria = data.auditoria || [];
  const form = $('#formConfig');
  for (const field of [
    'socio_estado_default',
    'socio_cobrador_default',
    'impresion_cobrador_default',
    'periodo_default',
    'moroso_cuotas_limite'
  ]) {
    if (form[field]) form[field].value = state.config[field] || '';
  }
  aplicarConfigUI();
  renderConfigCrud();
  renderAuditoria();
}

function cobradorTexto(numero) {
  const item = state.cobradores.find(cobrador => Number(cobrador.id) === Number(numero));
  return item ? item.nombre : '';
}

function tipoSocioTexto(id) {
  const item = state.tiposSocio.find(tipo => tipo.id === id);
  return item ? item.nombre : id;
}

function actualizarOpcionesCobrador(select, valores) {
  const value = select.value;
  select.innerHTML = '';
  for (const item of valores) {
    const option = document.createElement('option');
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  }
  if ([...select.options].some(option => option.value === value)) {
    select.value = value;
  }
}

function aplicarConfigUI() {
  const todos = [{ value: '', label: 'Todos los cobradores' }];
  const cobradoresActivos = state.cobradores.filter(cobrador => Number(cobrador.activo) === 1);
  const cobradores = cobradoresActivos.map(cobrador => ({
    value: String(cobrador.id),
    label: `${cobrador.id} - ${cobrador.nombre}`
  }));
  const impresion = cobradores;
  const tipos = state.tiposSocio
    .filter(tipo => Number(tipo.activo) === 1)
    .map(tipo => ({ value: tipo.id, label: tipo.nombre }));

  document.querySelectorAll('select[name="cobrador"]').forEach(select => {
    if (select.closest('#formFiltroCuotas')) {
      actualizarOpcionesCobrador(select, todos.concat(cobradores));
    } else if (select.closest('#formImprimir')) {
      actualizarOpcionesCobrador(select, impresion);
    } else {
      actualizarOpcionesCobrador(select, cobradores);
    }
  });
  if ($('#formConfig').socio_cobrador_default) {
    actualizarOpcionesCobrador($('#formConfig').socio_cobrador_default, cobradores);
  }
  if ($('#formConfig').impresion_cobrador_default) {
    actualizarOpcionesCobrador($('#formConfig').impresion_cobrador_default, impresion.length ? impresion : cobradores);
  }
  document.querySelectorAll('select[name="estado"]').forEach(select => {
    if (select.closest('#formFiltroCuotas') || select.closest('#formEditarCuota')) return;
    actualizarOpcionesCobrador(select, tipos);
  });
  if ($('#formConfig').socio_estado_default) {
    actualizarOpcionesCobrador($('#formConfig').socio_estado_default, tipos);
  }
}

function renderConfigCrud() {
  const tiposBody = $('#tiposSocioBody');
  const cobradoresBody = $('#cobradoresBody');
  if (tiposBody) {
    tiposBody.innerHTML = '';
    for (const tipo of state.tiposSocio) {
      const card = document.createElement('article');
      card.className = `config-item ${Number(tipo.activo) === 1 ? '' : 'inactive'}`;
      card.innerHTML = `
        <div>
          <strong>${tipo.nombre}</strong>
          <span>${money(tipo.monto)} por cuota</span>
          <small>${Number(tipo.activo) === 1 ? 'Disponible para nuevos socios' : 'Inactivo'}</small>
        </div>
        <div class="row-actions">
          <button type="button" class="secondary" data-edit-tipo="${tipo.id}">Editar</button>
          <button type="button" class="danger" data-delete-tipo="${tipo.id}">${Number(tipo.activo) === 1 ? 'Desactivar' : 'Eliminar'}</button>
        </div>
      `;
      tiposBody.appendChild(card);
    }
    tiposBody.querySelectorAll('[data-edit-tipo]').forEach(btn => {
      btn.addEventListener('click', () => editarTipoSocio(btn.dataset.editTipo));
    });
    tiposBody.querySelectorAll('[data-delete-tipo]').forEach(btn => {
      btn.addEventListener('click', () => borrarTipoSocio(btn.dataset.deleteTipo));
    });
  }
  if (cobradoresBody) {
    cobradoresBody.innerHTML = '';
    for (const cobrador of state.cobradores) {
      const card = document.createElement('article');
      card.className = `config-item ${Number(cobrador.activo) === 1 ? '' : 'inactive'}`;
      card.innerHTML = `
        <div>
          <strong>${cobrador.nombre}</strong>
          <span>Cobrador ${cobrador.id}</span>
          <small>${Number(cobrador.activo) === 1 ? 'Disponible para socios e impresion' : 'Inactivo'}</small>
        </div>
        <div class="row-actions">
          <button type="button" class="secondary" data-edit-cobrador="${cobrador.id}">Editar</button>
          <button type="button" class="danger" data-delete-cobrador="${cobrador.id}">${Number(cobrador.activo) === 1 ? 'Desactivar' : 'Eliminar'}</button>
        </div>
      `;
      cobradoresBody.appendChild(card);
    }
    cobradoresBody.querySelectorAll('[data-edit-cobrador]').forEach(btn => {
      btn.addEventListener('click', () => editarCobrador(Number(btn.dataset.editCobrador)));
    });
    cobradoresBody.querySelectorAll('[data-delete-cobrador]').forEach(btn => {
      btn.addEventListener('click', () => borrarCobrador(Number(btn.dataset.deleteCobrador)));
    });
  }
}

function renderAuditoria() {
  const body = $('#auditoriaBody');
  if (!body) return;
  body.innerHTML = '';
  if (!state.auditoria.length) {
    body.innerHTML = '<div class="empty-small">Sin acciones registradas.</div>';
    return;
  }
  for (const item of state.auditoria) {
    const row = document.createElement('div');
    row.className = 'audit-item';
    row.innerHTML = `
      <strong>${item.accion}</strong>
      <span>${item.detalle || '-'}</span>
      <small>${item.creado_en}</small>
    `;
    body.appendChild(row);
  }
}

function limpiarTipoSocio() {
  const form = $('#formTipoSocio');
  form.reset();
  form.id.value = '';
  form.activo.checked = true;
  $('#tipoSocioTitulo').textContent = 'Nuevo tipo de socio';
  abrir($('#modalTipoSocio'));
}

function limpiarCobrador() {
  const form = $('#formCobrador');
  form.reset();
  form.id.value = '';
  form.activo.checked = true;
  $('#cobradorTitulo').textContent = 'Nuevo cobrador';
  abrir($('#modalCobrador'));
}

function editarTipoSocio(id) {
  const tipo = state.tiposSocio.find(item => item.id === id);
  if (!tipo) return;
  const form = $('#formTipoSocio');
  form.id.value = tipo.id;
  form.nombre.value = tipo.nombre;
  form.monto.value = tipo.monto;
  form.activo.checked = Number(tipo.activo) === 1;
  $('#tipoSocioTitulo').textContent = `Editar ${tipo.nombre}`;
  abrir($('#modalTipoSocio'));
}

function editarCobrador(id) {
  const cobrador = state.cobradores.find(item => Number(item.id) === Number(id));
  if (!cobrador) return;
  const form = $('#formCobrador');
  form.id.value = cobrador.id;
  form.nombre.value = cobrador.nombre;
  form.activo.checked = Number(cobrador.activo) === 1;
  $('#cobradorTitulo').textContent = `Editar ${cobrador.nombre}`;
  abrir($('#modalCobrador'));
}

async function borrarTipoSocio(id) {
  if (!confirm('Dar de baja este tipo de socio? Si esta usado, quedara inactivo.')) return;
  await apiAdmin(
    `/api/config/tipos-socio/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
    'Autorizar baja de tipo de socio.'
  );
  await cargarConfig();
  await refrescarTodo();
  toast('Tipo de socio dado de baja');
}

async function borrarCobrador(id) {
  if (!confirm('Dar de baja este cobrador? Si esta usado, quedara inactivo.')) return;
  await apiAdmin(`/api/config/cobradores/${id}`, { method: 'DELETE' }, 'Autorizar baja de cobrador.');
  await cargarConfig();
  await refrescarTodo();
  toast('Cobrador dado de baja');
}

async function pagarCuota(cuotaId) {
  const request = { method: 'POST', body: '{}' };
  if (state.caja.dia && Number(state.caja.dia.cerrado) === 1) {
    return apiAdmin(`/api/cuotas/${cuotaId}/pagar`, request, 'Autorizar pago con caja cerrada.');
  }
  return api(`/api/cuotas/${cuotaId}/pagar`, request);
}

async function cargarDashboard() {
  const periodo = $('#formDashboard').periodo.value || periodoSiguiente();
  const data = await api(`/api/dashboard?periodo=${encodeURIComponent(periodo)}`);
  const dashboard = data.dashboard;
  $('#dashSociosTotal').textContent = dashboard.socios.total;
  $('#dashSociosTipo').textContent = `${dashboard.socios.activos} / ${dashboard.socios.jubilados}`;
  $('#dashCuotasPagadas').textContent = dashboard.cuotas_periodo.pagadas;
  $('#dashCuotasPendientes').textContent = dashboard.cuotas_periodo.pendientes;
  $('#dashRecaudado').textContent = money(dashboard.cuotas_periodo.recaudado);
  $('#dashPendiente').textContent = money(dashboard.cuotas_periodo.pendiente);
  $('#dashGlobal').textContent =
    `${dashboard.cuotas_global.total} cuotas: ${dashboard.cuotas_global.pagadas} pagas, ` +
    `${dashboard.cuotas_global.pendientes} impagas. Recaudado ${money(dashboard.cuotas_global.recaudado)}.`;

  const cobradores = $('#dashCobradores');
  cobradores.innerHTML = '';
  if (!dashboard.por_cobrador.length) {
    cobradores.innerHTML = '<span>Sin cuotas para el periodo.</span>';
    return;
  }
  for (const item of dashboard.por_cobrador) {
    const row = document.createElement('div');
    row.innerHTML = `<strong>${item.cobrador} - ${item.nombre}</strong><span>${item.cuotas} cuotas | ${money(item.recaudado)} recaudado | ${money(item.pendiente)} pendiente</span>`;
    cobradores.appendChild(row);
  }
}

async function cargarSocios() {
  const q = encodeURIComponent($('#buscar') ? $('#buscar').value.trim() : '');
  const data = await api(`/api/socios?q=${q}`);
  state.socios = data.socios;
  if ($('#proximoNro')) $('#proximoNro').textContent = data.proximo_nro_socio;
  $('#proximoNroCrud').textContent = data.proximo_nro_socio;
  if (!state.socioCrudId && $('#formNuevo')) $('#formNuevo').nro_socio.value = data.proximo_nro_socio;
  renderSocios();
  renderSociosCrud();
}

async function cargarSociosCrud() {
  const q = encodeURIComponent($('#buscarSocioCrud').value.trim());
  const data = await api(`/api/socios?q=${q}`);
  state.socios = data.socios;
  if ($('#proximoNro')) $('#proximoNro').textContent = data.proximo_nro_socio;
  $('#proximoNroCrud').textContent = data.proximo_nro_socio;
  if (!state.socioCrudId) $('#formNuevo').nro_socio.value = data.proximo_nro_socio;
  renderSocios();
  renderSociosCrud();
}

async function cargarCuotas() {
  const form = $('#formFiltroCuotas');
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(formData(form))) {
    if (value) params.set(key, value);
  }
  const data = await api(`/api/cuotas?${params.toString()}`);
  state.cuotas = data.cuotas;
  renderTablaCuotas();
  renderResumenCuotas();
}

async function cargarMorosos() {
  const data = await api('/api/socios/morosos');
  state.morosos = data.morosos;
  renderMorosos();
}

function renderSocios() {
  const body = $('#sociosBody');
  if (!body) return;
  body.innerHTML = '';
  for (const socio of state.socios) {
    const tr = document.createElement('tr');
    tr.className = socio.id === state.selectedId ? 'selected' : '';
    tr.innerHTML = `
      <td>${socio.nro_socio}</td>
      <td>${socio.apellido}, ${socio.nombre}</td>
      <td>${socio.dni}<br><small>${socio.telefono || ''} ${socio.email || ''}</small></td>
      <td>${tipoSocioTexto(socio.estado)}</td>
      <td>${socio.cobrador} - ${socio.cobrador_texto}</td>
      <td>${socio.cuotas_debe}</td>
      <td>${socio.cuotas_adelantadas}</td>
    `;
    tr.addEventListener('click', () => seleccionarSocio(socio.id));
    body.appendChild(tr);
  }
}

function renderSociosCrud() {
  const body = $('#sociosCrudBody');
  body.innerHTML = '';
  if (!state.socios.length) {
    body.innerHTML = '<tr><td colspan="3">No hay socios para mostrar.</td></tr>';
    return;
  }
  for (const socio of state.socios) {
    const tr = document.createElement('tr');
    tr.className = socio.id === state.socioCrudId ? 'selected' : '';
    tr.innerHTML = `
      <td>${socio.nro_socio}</td>
      <td>${socio.apellido}, ${socio.nombre}</td>
      <td>${socio.dni}</td>
    `;
    tr.addEventListener('click', () => cargarSocioEnCrud(socio.id));
    body.appendChild(tr);
  }
}

async function cargarSocioEnCrud(id) {
  const data = await api(`/api/socios/${id}`);
  const socio = data.socio;
  state.socioCrudId = id;
  $('#socioCrudTitulo').textContent = `#${socio.nro_socio} ${socio.apellido}, ${socio.nombre}`;
  $('#socioCrudMeta').textContent = `${socio.dni} | ${socio.direccion} | ${socio.cobrador_texto}`;
  $('#socioCrudContacto').innerHTML = `
    <strong>Contacto</strong>
    <span>Telefono: ${socio.telefono || '-'}</span>
    <span>Email: ${socio.email || '-'}</span>
    <span>Debe ${socio.cuotas_debe} cuota(s) | Adelantadas ${socio.cuotas_adelantadas}</span>
  `;
  renderCuotasSocioCrud(data.cuotas);
  $('#btnSocioBajaCrud').disabled = false;
  $('#btnSocioEditarCrud').disabled = false;
  renderSociosCrud();
}

function renderCuotasSocioCrud(cuotas) {
  const box = $('#socioCrudCuotas');
  box.innerHTML = '';
  if (!cuotas.length) {
    box.innerHTML = '<div class="empty">Este socio no tiene cuotas.</div>';
    return;
  }
  for (const cuota of cuotas) {
    const item = document.createElement('div');
    item.className = `cuota ${cuota.estado}`;
    item.innerHTML = `
      <div>
        <strong>${cuota.periodo}</strong> - $${Number(cuota.monto).toFixed(2)} - ${cuota.estado}
        <small>${cuota.fecha_pago ? `Pagada el ${cuota.fecha_pago}` : 'Impaga / pendiente'}</small>
      </div>
    `;
    box.appendChild(item);
  }
}

async function abrirModalSocio(id = null) {
  if (!id) {
    resetNuevoSocio();
    abrir($('#modalSocioForm'));
    return;
  }
  const data = await api(`/api/socios/${id}`);
  const socio = data.socio;
  const form = $('#formNuevo');
  form.id.value = socio.id;
  for (const field of ['nro_socio', 'dni', 'apellido', 'nombre', 'telefono', 'email', 'direccion', 'barrio', 'localidad', 'fecha_nacimiento', 'fecha_alta', 'ocupacion', 'estado', 'cobrador']) {
    form[field].value = socio[field] ?? '';
  }
  $('#socioFormTitulo').textContent = `Modificar socio #${socio.nro_socio}`;
  abrir($('#modalSocioForm'));
}

async function seleccionarSocio(id) {
  if (!$('#detalle')) return;
  state.selectedId = id;
  renderSocios();
  const data = await api(`/api/socios/${id}`);
  const socio = data.socio;
  $('#detalleVacio').hidden = true;
  $('#detalle').hidden = false;
  $('#detalleNombre').textContent = `#${socio.nro_socio} ${socio.apellido}, ${socio.nombre}`;
  $('#detalleMeta').textContent = `${socio.direccion} | Debe ${socio.cuotas_debe} cuota(s) | Adelantadas ${socio.cuotas_adelantadas}`;

  const form = $('#formSocio');
  for (const field of ['nro_socio', 'dni', 'apellido', 'nombre', 'telefono', 'email', 'direccion', 'barrio', 'localidad', 'fecha_nacimiento', 'fecha_alta', 'ocupacion', 'estado', 'cobrador']) {
    form[field].value = socio[field] ?? '';
  }
  renderCuotas(data.cuotas);
}

function renderCuotas(cuotas) {
  const box = $('#cuotas');
  box.innerHTML = '';
  if (!cuotas.length) {
    box.innerHTML = '<div class="empty">Sin cuotas cargadas.</div>';
    return;
  }
  for (const cuota of cuotas) {
    const item = document.createElement('div');
    item.className = `cuota ${cuota.estado}`;
    const accion = cuota.estado === 'pagada'
      ? `<button class="secondary" data-pendiente="${cuota.id}">Volver pendiente</button>`
      : `<button data-pagar="${cuota.id}">Marcar pagada</button>`;
    item.innerHTML = `
      <div>
        <strong>${cuota.periodo}</strong> - $${Number(cuota.monto).toFixed(2)} - ${cuota.estado}
        <small>${cuota.fecha_pago ? `Pagada el ${cuota.fecha_pago}` : 'Pendiente de pago'}</small>
      </div>
      <div>${accion}</div>
    `;
    box.appendChild(item);
  }
  box.querySelectorAll('[data-pagar]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await pagarCuota(btn.dataset.pagar);
      await seleccionarSocio(state.selectedId);
      await cargarSocios();
      if ($('#paginaCaja') && !$('#paginaCaja').hidden) await cargarCaja();
    });
  });
  box.querySelectorAll('[data-pendiente]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await apiAdmin(
        `/api/cuotas/${btn.dataset.pendiente}/pendiente`,
        { method: 'POST', body: '{}' },
        'Autorizar despago de cuota.'
      );
      await seleccionarSocio(state.selectedId);
      await cargarSocios();
      if ($('#paginaCaja') && !$('#paginaCaja').hidden) await cargarCaja();
    });
  });
}

function renderTablaCuotas() {
  const body = $('#cuotasBody');
  body.innerHTML = '';
  if (!state.cuotas.length) {
    body.innerHTML = '<tr><td colspan="7">No hay cuotas para los filtros seleccionados.</td></tr>';
    return;
  }
  for (const cuota of state.cuotas) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${cuota.periodo}</td>
      <td>#${cuota.nro_socio} ${cuota.socio}<br><small>${cuota.dni} - ${cuota.direccion}</small></td>
      <td>${cuota.cobrador} - ${cuota.cobrador_texto}</td>
      <td>$${Number(cuota.monto).toFixed(2)}</td>
      <td>${cuota.estado}</td>
      <td>${cuota.fecha_pago || '-'}</td>
      <td class="row-actions">
        <button class="secondary" data-edit-cuota="${cuota.id}">Editar</button>
        ${cuota.estado === 'pagada'
          ? `<button class="secondary" data-pendiente-cuota="${cuota.id}">Pendiente</button>`
          : `<button data-pagar-cuota="${cuota.id}">Pagar</button>`}
        <button class="danger" data-delete-cuota="${cuota.id}">Eliminar</button>
      </td>
    `;
    body.appendChild(tr);
  }
  body.querySelectorAll('[data-edit-cuota]').forEach(btn => {
    btn.addEventListener('click', () => abrirEditorCuota(Number(btn.dataset.editCuota)));
  });
  body.querySelectorAll('[data-pagar-cuota]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await pagarCuota(btn.dataset.pagarCuota);
      await refrescarTodo();
      toast('Cuota pagada e ingreso registrado en caja');
    });
  });
  body.querySelectorAll('[data-pendiente-cuota]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await apiAdmin(
        `/api/cuotas/${btn.dataset.pendienteCuota}/pendiente`,
        { method: 'POST', body: '{}' },
        'Autorizar despago de cuota.'
      );
      await refrescarTodo();
      toast('Cuota pendiente e ingreso quitado de caja');
    });
  });
  body.querySelectorAll('[data-delete-cuota]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Eliminar esta cuota?')) return;
      await apiAdmin(
        `/api/cuotas/${btn.dataset.deleteCuota}`,
        { method: 'DELETE' },
        'Autorizar eliminacion de cuota.'
      );
      await refrescarTodo();
      toast('Cuota eliminada');
    });
  });
}

function renderResumenCuotas() {
  const total = state.cuotas.length;
  const pendientes = state.cuotas.filter(cuota => cuota.estado === 'pendiente');
  const pagadas = state.cuotas.filter(cuota => cuota.estado === 'pagada');
  const montoPendiente = pendientes.reduce((acc, cuota) => acc + Number(cuota.monto || 0), 0);
  $('#cuotasTotal').textContent = total;
  $('#cuotasPendientes').textContent = pendientes.length;
  $('#cuotasPagadas').textContent = pagadas.length;
  $('#cuotasMontoPendiente').textContent = `$${montoPendiente.toFixed(2)}`;
}

function renderMorosos() {
  const body = $('#morososBody');
  if (!body) return;
  body.innerHTML = '';
  if (!state.morosos.length) {
    body.innerHTML = '<tr><td colspan="6">No hay socios morosos con el limite actual.</td></tr>';
    return;
  }
  for (const socio of state.morosos) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${socio.nro_socio}</td>
      <td>${socio.apellido}, ${socio.nombre}<br><small>${socio.dni}</small></td>
      <td>${socio.telefono || '-'}<br><small>${socio.email || ''}</small></td>
      <td>${socio.cobrador} - ${socio.cobrador_texto}</td>
      <td>${socio.cuotas_impagas}</td>
      <td>${money(socio.deuda)}</td>
    `;
    body.appendChild(tr);
  }
}

function abrirPagoAdelantado() {
  const form = $('#formPagoAdelantado');
  form.reset();
  const select = form.socio_id;
  select.innerHTML = '';
  for (const socio of state.socios) {
    const option = document.createElement('option');
    option.value = socio.id;
    option.textContent = `#${socio.nro_socio} ${socio.apellido}, ${socio.nombre}`;
    select.appendChild(option);
  }
  const selected = state.socioCrudId || state.selectedId;
  if (selected) select.value = String(selected);
  form.desde_periodo.value = periodoDefault();
  form.fecha_pago.value = fechaActual();
  form.cantidad.value = 1;
  abrir($('#modalPagoAdelantado'));
}

async function cargarCaja() {
  const fecha = $('#formCajaDia') ? $('#formCajaDia').fecha.value || fechaActual() : fechaActual();
  const data = await api(`/api/caja?fecha=${encodeURIComponent(fecha)}`);
  state.caja = {
    dia: data.dia,
    movimientos: data.movimientos,
    resumen: data.resumen
  };
  renderCaja();
}

function renderCaja() {
  const form = $('#formCajaDia');
  if (!form || !state.caja.dia) return;
  form.fecha.value = state.caja.dia.fecha;
  form.saldo_inicial.value = state.caja.dia.saldo_inicial;
  form.observacion.value = state.caja.dia.observacion || '';
  form.cerrado.checked = Number(state.caja.dia.cerrado) === 1;
  $('#cajaSaldoInicial').textContent = money(state.caja.resumen.saldo_inicial);
  $('#cajaIngresos').textContent = money(state.caja.resumen.ingresos);
  $('#cajaEgresos').textContent = money(state.caja.resumen.egresos);
  $('#cajaSaldoFinal').textContent = money(state.caja.resumen.saldo_final);
  $('#cajaCantidad').textContent = `${state.caja.resumen.cantidad_movimientos} movimiento(s) del dia.`;

  const body = $('#cajaMovimientosBody');
  body.innerHTML = '';
  if (!state.caja.movimientos.length) {
    body.innerHTML = '<tr><td colspan="6">No hay movimientos cargados para esta fecha.</td></tr>';
    return;
  }
  for (const movimiento of state.caja.movimientos) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="badge ${movimiento.tipo}">${movimiento.tipo}</span></td>
      <td>${movimiento.concepto}</td>
      <td>${movimiento.medio_pago}</td>
      <td>${money(movimiento.monto)}</td>
      <td>${movimiento.descripcion || '-'}<br><small>${movimiento.referencia || ''}</small></td>
      <td class="row-actions">
        <button type="button" class="secondary" data-edit-caja="${movimiento.id}">Editar</button>
        <button type="button" class="danger" data-delete-caja="${movimiento.id}">Eliminar</button>
      </td>
    `;
    body.appendChild(tr);
  }
  body.querySelectorAll('[data-edit-caja]').forEach(btn => {
    btn.addEventListener('click', () => abrirMovimientoCaja(null, Number(btn.dataset.editCaja)));
  });
  body.querySelectorAll('[data-delete-caja]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Eliminar este movimiento de caja?')) return;
      await apiAdmin(
        `/api/caja/movimientos/${btn.dataset.deleteCaja}`,
        { method: 'DELETE' },
        'Autorizar eliminacion de movimiento de caja.'
      );
      await cargarCaja();
      toast('Movimiento eliminado');
    });
  });
}

function abrirMovimientoCaja(tipo, id = null) {
  const form = $('#formCajaMovimiento');
  form.reset();
  form.id.value = '';
  form.fecha.value = $('#formCajaDia').fecha.value || fechaActual();
  form.tipo.value = tipo || 'ingreso';
  $('#cajaMovimientoTitulo').textContent = tipo === 'egreso' ? 'Nuevo egreso' : 'Nuevo ingreso';
  if (id) {
    const movimiento = state.caja.movimientos.find(item => item.id === id);
    if (!movimiento) return;
    form.id.value = movimiento.id;
    form.fecha.value = movimiento.fecha;
    form.tipo.value = movimiento.tipo;
    form.concepto.value = movimiento.concepto;
    form.monto.value = movimiento.monto;
    form.medio_pago.value = movimiento.medio_pago;
    form.descripcion.value = movimiento.descripcion || '';
    form.referencia.value = movimiento.referencia || '';
    $('#cajaMovimientoTitulo').textContent = `Editar ${movimiento.tipo}`;
  }
  abrir($('#modalCajaMovimiento'));
}

function abrirEditorCuota(id) {
  const cuota = state.cuotas.find(item => item.id === id);
  if (!cuota) return;
  const form = $('#formEditarCuota');
  form.id.value = cuota.id;
  form.periodo.value = cuota.periodo;
  form.monto.value = cuota.monto;
  form.estado.value = cuota.estado;
  form.fecha_pago.value = cuota.fecha_pago || '';
  form.observacion.value = cuota.observacion || '';
  abrir($('#modalCuota'));
}

async function refrescarTodo() {
  await cargarDashboard();
  await cargarSocios();
  await cargarCuotas();
  await cargarMorosos();
  if ($('#paginaCaja') && !$('#paginaCaja').hidden) {
    await cargarCaja();
  }
  if (state.selectedId && $('#detalle')) {
    await seleccionarSocio(state.selectedId);
  }
}

function abrir(dialog) {
  dialog.showModal();
}

function mostrarPaginaSocios() {
  $('#paginaInicio').hidden = true;
  $('#paginaSocios').hidden = false;
  $('#paginaCuotas').hidden = true;
  $('#paginaConfig').hidden = true;
  $('#paginaCaja').hidden = true;
  resetNuevoSocio();
  $('#btnSocioBajaCrud').disabled = true;
  $('#btnSocioEditarCrud').disabled = true;
  $('#socioCrudTitulo').textContent = 'Seleccione un socio';
  $('#socioCrudMeta').textContent = 'Click sobre un socio para ver sus cuotas pagas e impagas.';
  $('#socioCrudContacto').innerHTML = '';
  $('#socioCrudCuotas').innerHTML = '';
  cargarSociosCrud();
}

function mostrarPaginaCuotas() {
  $('#paginaInicio').hidden = true;
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = false;
  $('#paginaConfig').hidden = true;
  $('#paginaCaja').hidden = true;
  cargarCuotas();
  cargarMorosos();
}

function mostrarPaginaInicio() {
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = true;
  $('#paginaConfig').hidden = true;
  $('#paginaCaja').hidden = true;
  $('#paginaInicio').hidden = false;
  resetNuevoSocio();
}

function mostrarPaginaConfig() {
  $('#paginaInicio').hidden = true;
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = true;
  $('#paginaConfig').hidden = false;
  $('#paginaCaja').hidden = true;
  cargarConfig();
}

function mostrarPaginaCaja() {
  $('#paginaInicio').hidden = true;
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = true;
  $('#paginaConfig').hidden = true;
  $('#paginaCaja').hidden = false;
  if (!$('#formCajaDia').fecha.value) $('#formCajaDia').fecha.value = fechaActual();
  cargarCaja();
}

function imprimirCuotas(cobrador) {
  const periodo = $('#formFiltroCuotas').periodo.value || $('#formImprimir').periodo.value || periodoSiguiente();
  const cobradorFinal = cobrador || state.config.impresion_cobrador_default || 1;
  window.open(`/imprimir?periodo=${encodeURIComponent(periodo)}&cobrador=${cobradorFinal}`, '_blank');
}

function cerrarDialogs() {
  document.querySelectorAll('dialog').forEach(d => d.close());
}

async function init() {
  await cargarConfig();
  const periodo = periodoDefault();
  $('#formDashboard').periodo.value = periodo;
  $('#formGenerar').periodo.value = periodo;
  $('#formImprimir').periodo.value = periodo;
  $('#formImprimir').cobrador.value = state.config.impresion_cobrador_default || '1';
  if ($('#formCuota')) $('#formCuota').periodo.value = periodo;
  $('#formFiltroCuotas').periodo.value = periodo;
  $('#formCajaDia').fecha.value = fechaActual();

  if ($('#btnBuscar')) $('#btnBuscar').addEventListener('click', cargarSocios);
  if ($('#buscar')) {
    $('#buscar').addEventListener('keydown', (event) => {
      if (event.key === 'Enter') cargarSocios();
    });
  }

  $('#formDashboard').addEventListener('submit', async (event) => {
    event.preventDefault();
    await cargarDashboard();
  });

  $('#btnInicio').addEventListener('click', mostrarPaginaInicio);
  $('#btnNuevo').addEventListener('click', () => {
    mostrarPaginaSocios();
  });
  $('#btnCuotas').addEventListener('click', mostrarPaginaCuotas);
  $('#btnCaja').addEventListener('click', mostrarPaginaCaja);
  $('#btnVolverInicio').addEventListener('click', mostrarPaginaInicio);
  $('#btnVolverInicioCuotas').addEventListener('click', mostrarPaginaInicio);
  $('#btnCajaVolver').addEventListener('click', mostrarPaginaInicio);
  $('#btnVolverInicioConfig').addEventListener('click', mostrarPaginaInicio);
  $('#btnConfigCancelar').addEventListener('click', mostrarPaginaInicio);
  $('#btnConfig').addEventListener('click', mostrarPaginaConfig);
  $('#btnTipoSocioNuevo').addEventListener('click', limpiarTipoSocio);
  $('#btnCobradorNuevo').addEventListener('click', limpiarCobrador);
  document.querySelectorAll('[data-close]').forEach(btn => btn.addEventListener('click', cerrarDialogs));
  $('#btnBuscarSocioCrud').addEventListener('click', cargarSociosCrud);
  $('#buscarSocioCrud').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') cargarSociosCrud();
  });
  $('#btnSocioNuevoModo').addEventListener('click', () => abrirModalSocio());
  $('#btnSocioEditarCrud').addEventListener('click', () => {
    if (state.socioCrudId) abrirModalSocio(state.socioCrudId);
  });
  $('#btnCajaIngreso').addEventListener('click', () => abrirMovimientoCaja('ingreso'));
  $('#btnCajaEgreso').addEventListener('click', () => abrirMovimientoCaja('egreso'));
  $('#btnCajaActualizar').addEventListener('click', cargarCaja);
  $('#btnPagoAdelantado').addEventListener('click', abrirPagoAdelantado);
  $('#btnActualizarMorosos').addEventListener('click', cargarMorosos);
  $('#btnImprimirMorosos').addEventListener('click', () => window.open('/imprimir-morosos', '_blank'));
  $('#formCajaDia').fecha.addEventListener('change', cargarCaja);
  $('#formAdminClave').addEventListener('submit', (event) => {
    event.preventDefault();
    const clave = event.currentTarget.clave.value;
    cerrarDialogs();
    if (adminKeyResolve) adminKeyResolve(clave);
    adminKeyResolve = null;
    adminKeyReject = null;
  });
  $('#btnAdminCancelar').addEventListener('click', () => {
    cerrarDialogs();
    if (adminKeyResolve) adminKeyResolve('');
    adminKeyResolve = null;
    adminKeyReject = null;
  });

  $('#formNuevo').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const id = data.id;
    delete data.id;
    if (id) {
      await api(`/api/socios/${id}`, { method: 'PUT', body: JSON.stringify(data) });
      await refrescarTodo();
      await cargarSocioEnCrud(Number(id));
      cerrarDialogs();
      toast('Socio modificado');
    } else {
      const result = await api('/api/socios', { method: 'POST', body: JSON.stringify(data) });
      await refrescarTodo();
      await cargarSocioEnCrud(result.id);
      cerrarDialogs();
      toast(`Socio creado con nro. ${result.nro_socio}`);
    }
  });

  $('#btnSocioBajaCrud').addEventListener('click', async () => {
    if (!state.socioCrudId) return;
    if (!confirm('Dar de baja este socio? Se eliminaran sus cuotas y el numero quedara libre.')) return;
    const result = await apiAdmin(
      `/api/socios/${state.socioCrudId}`,
      { method: 'DELETE' },
      'Autorizar baja de socio.'
    );
    if (state.selectedId === state.socioCrudId && $('#detalle')) {
      state.selectedId = null;
      $('#detalle').hidden = true;
      $('#detalleVacio').hidden = false;
    }
    resetNuevoSocio();
    await refrescarTodo();
    toast(`Baja realizada. Nro. ${result.nro_liberado} disponible.`);
  });

  if ($('#formSocio')) {
    $('#formSocio').addEventListener('submit', async (event) => {
      event.preventDefault();
      await api(`/api/socios/${state.selectedId}`, {
        method: 'PUT',
        body: JSON.stringify(formData(event.currentTarget))
      });
      await refrescarTodo();
      toast('Socio actualizado');
    });
  }

  if ($('#btnBaja')) {
    $('#btnBaja').addEventListener('click', async () => {
      if (!state.selectedId) return;
      if (!confirm('Dar de baja este socio? Se eliminaran sus cuotas y el numero quedara libre.')) return;
      const result = await apiAdmin(`/api/socios/${state.selectedId}`, { method: 'DELETE' }, 'Autorizar baja de socio.');
      state.selectedId = null;
      $('#detalle').hidden = true;
      $('#detalleVacio').hidden = false;
      await refrescarTodo();
      toast(`Baja realizada. Nro. ${result.nro_liberado} disponible.`);
    });
  }

  if ($('#formCuota')) {
    $('#formCuota').addEventListener('submit', async (event) => {
      event.preventDefault();
      const data = formData(event.currentTarget);
      data.socio_id = state.selectedId;
      await api('/api/cuotas', { method: 'POST', body: JSON.stringify(data) });
      await refrescarTodo();
      toast('Cuota agregada');
    });
  }

  $('#formGenerar').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const result = await api('/api/cuotas/generar', { method: 'POST', body: JSON.stringify(data) });
    $('#formFiltroCuotas').periodo.value = result.periodo;
    await refrescarTodo();
    toast(`Generadas ${result.cuotas_creadas} cuota(s) para ${result.periodo}`);
  });

  $('#formImprimir').addEventListener('submit', (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    window.open(`/imprimir?periodo=${encodeURIComponent(data.periodo)}&cobrador=${data.cobrador}`, '_blank');
  });

  $('#btnPrintCobrador').addEventListener('click', () => imprimirCuotas());
  $('#btnPrintBiblioteca').addEventListener('click', () => imprimirCuotas(3));

  $('#formConfig').addEventListener('submit', async (event) => {
    event.preventDefault();
    await apiAdmin(
      '/api/config',
      { method: 'POST', body: JSON.stringify(formData(event.currentTarget)) },
      'Autorizar cambio de configuracion.'
    );
    await cargarConfig();
    await refrescarTodo();
    toast('Predeterminados guardados');
  });

  $('#formCajaDia').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    data.cerrado = event.currentTarget.cerrado.checked ? '1' : '0';
    const request = { method: 'POST', body: JSON.stringify(data) };
    if (state.caja.dia && Number(state.caja.dia.cerrado) === 1) {
      await apiAdmin('/api/caja/dia', request, 'Autorizar modificacion de caja cerrada.');
    } else {
      await api('/api/caja/dia', request);
    }
    await cargarCaja();
    toast('Caja diaria guardada');
  });

  $('#formSeguridad').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    if (data.clave_nueva !== data.clave_repetida) {
      toast('La nueva clave no coincide');
      return;
    }
    await api('/api/config/seguridad', { method: 'POST', body: JSON.stringify(data) });
    event.currentTarget.reset();
    await cargarConfig();
    toast('Clave de administrador actualizada');
  });

  $('#formCajaMovimiento').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const id = data.id;
    delete data.id;
    if (id) {
      await apiAdmin(
        `/api/caja/movimientos/${id}`,
        { method: 'PUT', body: JSON.stringify(data) },
        'Autorizar edicion de movimiento de caja.'
      );
      toast('Movimiento actualizado');
    } else {
      const closed = state.caja.dia && Number(state.caja.dia.cerrado) === 1;
      const request = { method: 'POST', body: JSON.stringify(data) };
      if (closed) {
        await apiAdmin('/api/caja/movimientos', request, 'Autorizar movimiento en caja cerrada.');
      } else {
        await api('/api/caja/movimientos', request);
      }
      toast('Movimiento cargado');
    }
    cerrarDialogs();
    await cargarCaja();
  });

  $('#formPagoAdelantado').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const request = { method: 'POST', body: JSON.stringify(data) };
    const cajaCerrada = state.caja.dia && state.caja.dia.fecha === data.fecha_pago && Number(state.caja.dia.cerrado) === 1;
    const result = cajaCerrada
      ? await apiAdmin('/api/cuotas/adelanto', request, 'Autorizar pago adelantado en caja cerrada.')
      : await api('/api/cuotas/adelanto', request);
    cerrarDialogs();
    await refrescarTodo();
    const cajaMsg = data.medio_pago === 'efectivo' ? ' Ingreso registrado en caja.' : ' No mueve caja diaria.';
    toast(`Pago adelantado: ${result.cuotas_pagadas} cuota(s) pagada(s).${cajaMsg}`);
  });

  $('#formTipoSocio').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    data.activo = event.currentTarget.activo.checked ? '1' : '0';
    const id = data.id;
    delete data.id;
    if (id) {
      await apiAdmin(
        `/api/config/tipos-socio/${encodeURIComponent(id)}`,
        { method: 'PUT', body: JSON.stringify(data) },
        'Autorizar edicion de tipo de socio.'
      );
      toast('Tipo de socio actualizado');
    } else {
      await apiAdmin(
        '/api/config/tipos-socio',
        { method: 'POST', body: JSON.stringify(data) },
        'Autorizar alta de tipo de socio.'
      );
      toast('Tipo de socio creado');
    }
    cerrarDialogs();
    $('#formTipoSocio').reset();
    await cargarConfig();
    await refrescarTodo();
  });

  $('#formCobrador').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    data.activo = event.currentTarget.activo.checked ? '1' : '0';
    const id = data.id;
    delete data.id;
    if (id) {
      await apiAdmin(
        `/api/config/cobradores/${id}`,
        { method: 'PUT', body: JSON.stringify(data) },
        'Autorizar edicion de cobrador.'
      );
      toast('Cobrador actualizado');
    } else {
      await apiAdmin(
        '/api/config/cobradores',
        { method: 'POST', body: JSON.stringify(data) },
        'Autorizar alta de cobrador.'
      );
      toast('Cobrador creado');
    }
    cerrarDialogs();
    $('#formCobrador').reset();
    await cargarConfig();
    await refrescarTodo();
  });

  $('#btnRecargarCuotas').addEventListener('click', cargarCuotas);

  $('#formFiltroCuotas').addEventListener('submit', async (event) => {
    event.preventDefault();
    await cargarCuotas();
  });

  $('#formEditarCuota').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const id = data.id;
    delete data.id;
    await apiAdmin(
      `/api/cuotas/${id}`,
      { method: 'PUT', body: JSON.stringify(data) },
      'Autorizar modificacion de cuota.'
    );
    cerrarDialogs();
    await refrescarTodo();
    toast(data.estado === 'pagada' ? 'Cuota modificada e ingreso registrado en caja' : 'Cuota modificada sin ingreso en caja');
  });

  await cargarDashboard();
  await cargarSocios();
  await cargarCuotas();
  await cargarMorosos();
  await cargarCaja();
}

init().catch(error => toast(error.message));
