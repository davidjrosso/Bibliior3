const state = {
  socios: [],
  cuotas: [],
  faltantesCuotas: {
    desde: '',
    hasta: '',
    total: 0,
    mostrados: 0,
    resumen: [],
    faltantes: []
  },
  morosos: [],
  selectedId: null,
  socioCrudId: null,
  config: {},
  tiposSocio: [],
  cobradores: [],
  auditoria: [],
  usuario: '',
  socioCrudCuotas: [],
  socioCuotasFiltro: 'pendiente',
  caja: {
    dia: null,
    movimientos: [],
    resumen: {}
  },
  cajaListado: {
    dias: [],
    resumen: {}
  }
};

const $ = (selector) => document.querySelector(selector);
let adminKeyResolve = null;
let adminKeyReject = null;
let authEventsBound = false;
let pagoAdelantadoSearchTimer = null;
let cuotasSeleccionadasSocio = new Set();

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

function sumarMesesPeriodo(periodo, meses) {
  const [year, month] = periodo.split('-').map(Number);
  const date = new Date(year, month - 1 + meses, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

function fechaActual() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function fechaHace(dias) {
  const date = new Date();
  date.setDate(date.getDate() - dias);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function periodoDefault() {
  return state.config.periodo_default === 'actual' ? periodoActual() : periodoSiguiente();
}

function modoBusquedaSocio(selector) {
  return $(selector)?.checked ? 'todos' : 'nro';
}

function actualizarModoBusquedaSocio(inputSelector, toggleSelector) {
  const input = $(inputSelector);
  if (!input) return;
  input.placeholder = modoBusquedaSocio(toggleSelector) === 'todos'
    ? 'Nombre, apellido, DNI, direccion, telefono o correo'
    : 'Nro. de socio';
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
  if (response.status === 401 && !url.startsWith('/api/auth/')) {
    mostrarLogin();
  }
  if (!response.ok || data.exito === false) {
    const error = new Error(data.error || 'Error de operacion');
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

async function obtenerSesion() {
  return api('/api/auth/session');
}

function configurarAcceso() {
  if (authEventsBound) return;
  authEventsBound = true;
  $('#formLogin').addEventListener('submit', async (event) => {
    event.preventDefault();
    await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(formData(event.currentTarget))
    });
    window.location.reload();
  });
  $('#btnLogout').addEventListener('click', async () => {
    await api('/api/auth/logout', { method: 'POST', body: '{}' });
    window.location.reload();
  });
}

function mostrarLogin() {
  $('#loginScreen').hidden = false;
  $('#appTopbar').hidden = true;
  ['#paginaInicio', '#paginaSocios', '#paginaCuotas', '#paginaConfig', '#paginaCaja'].forEach(selector => {
    const el = $(selector);
    if (el) el.hidden = true;
  });
}

function mostrarSistema() {
  $('#loginScreen').hidden = true;
  $('#appTopbar').hidden = false;
  $('#paginaInicio').hidden = false;
}

function pedirClaveAdmin(motivo) {
  const dialog = $('#modalAdminClave');
  const form = $('#formAdminClave');
  if (!dialog || !form) {
    return Promise.resolve(window.prompt(`${motivo || 'Esta accion requiere permiso.'}\n\nIngrese clave de administrador:`) || '');
  }
  return new Promise((resolve) => {
    adminKeyResolve = resolve;
    adminKeyReject = null;
    $('#adminClaveMotivo').textContent = motivo || 'Esta accion requiere permiso.';
    form.reset();
    abrir(dialog);
    setTimeout(() => form.clave.focus(), 60);
  });
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

async function apiConClaveSiHaceFalta(url, options = {}, motivo = '') {
  try {
    return await api(url, options);
  } catch (error) {
    const requiereClave = error.status === 403 && String(error.message || '').toLowerCase().includes('clave');
    if (!requiereClave) throw error;
    return apiAdmin(url, options, motivo || error.message);
  }
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

const formatoNumero = new Intl.NumberFormat('es-AR');
const formatoDinero = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

function number(value) {
  return formatoNumero.format(Number(value || 0));
}

function decimalInput(value) {
  return Number(value || 0).toLocaleString('es-AR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function money(value) {
  return formatoDinero.format(Number(value || 0)).replace(/\s/g, ' ');
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
  if ($('#formAcceso').usuario) $('#formAcceso').usuario.value = state.config.login_user || state.usuario || 'admin';
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
  form.monto.value = decimalInput(tipo.monto);
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
  const request = {
    method: 'POST',
    body: JSON.stringify({ fecha_pago: fechaActual(), medio_pago: 'efectivo' })
  };
  return apiConClaveSiHaceFalta(`/api/cuotas/${cuotaId}/pagar`, request, 'Autorizar pago con caja cerrada.');
}

async function pagarCuotasSocioSeleccionadas() {
  const ids = Array.from(cuotasSeleccionadasSocio);
  if (!ids.length) {
    toast('Seleccione al menos una cuota impaga');
    return;
  }
  const fechaPago = $('#socioPagoFecha').value || fechaActual();
  const medioPago = $('#socioPagoMedio').value || 'efectivo';
  const total = state.socioCrudCuotas
    .filter(cuota => cuotasSeleccionadasSocio.has(Number(cuota.id)))
    .reduce((acc, cuota) => acc + Number(cuota.monto || 0), 0);
  const cajaMsg = medioPago === 'efectivo'
    ? 'El efectivo se registrara en caja diaria.'
    : 'Este medio no mueve caja diaria.';
  if (!confirm(`Cobrar ${number(ids.length)} cuota(s) por ${money(total)}?\n\n${cajaMsg}`)) return;
  const request = {
    method: 'POST',
    body: JSON.stringify({ ids, fecha_pago: fechaPago, medio_pago: medioPago })
  };
  const result = await apiConClaveSiHaceFalta('/api/cuotas/pagar', request, 'Autorizar pago con caja cerrada.');
  cuotasSeleccionadasSocio = new Set();
  await refrescarTodo();
  if (state.socioCrudId) await cargarSocioEnCrud(state.socioCrudId);
  await cargarCajaListado();
  toast(`Cobro registrado: ${number(result.cuotas_pagadas)} cuota(s).`);
}

async function cargarDashboard() {
  const periodo = $('#formDashboard').periodo.value || periodoSiguiente();
  const data = await api(`/api/dashboard?periodo=${encodeURIComponent(periodo)}`);
  const dashboard = data.dashboard;
  $('#dashSociosTotal').textContent = number(dashboard.socios.total);
  $('#dashSociosTipo').textContent = `${number(dashboard.socios.activos)} / ${number(dashboard.socios.jubilados)}`;
  $('#dashCuotasPagadas').textContent = number(dashboard.cuotas_periodo.pagadas);
  $('#dashCuotasPendientes').textContent = number(dashboard.cuotas_periodo.pendientes);
  $('#dashRecaudado').textContent = money(dashboard.cuotas_periodo.recaudado);
  $('#dashPendiente').textContent = money(dashboard.cuotas_periodo.pendiente);
  $('#dashGlobal').textContent =
    `${number(dashboard.cuotas_global.total)} cuotas: ${number(dashboard.cuotas_global.pagadas)} pagas, ` +
    `${number(dashboard.cuotas_global.pendientes)} impagas. Recaudado ${money(dashboard.cuotas_global.recaudado)}.`;

  const cobradores = $('#dashCobradores');
  cobradores.innerHTML = '';
  if (!dashboard.por_cobrador.length) {
    cobradores.innerHTML = '<span>Sin cuotas para el periodo.</span>';
    return;
  }
  for (const item of dashboard.por_cobrador) {
    const row = document.createElement('div');
    row.innerHTML = `<strong>${item.cobrador} - ${item.nombre}</strong><span>${number(item.cuotas)} cuotas | ${money(item.recaudado)} recaudado | ${money(item.pendiente)} pendiente</span>`;
    cobradores.appendChild(row);
  }
}

async function cargarSocios() {
  const q = encodeURIComponent($('#buscar') ? $('#buscar').value.trim() : '');
  const data = await api(`/api/socios?q=${q}&modo_busqueda=todos`);
  state.socios = data.socios;
  if ($('#proximoNro')) $('#proximoNro').textContent = data.proximo_nro_socio;
  $('#proximoNroCrud').textContent = data.proximo_nro_socio;
  if (!state.socioCrudId && $('#formNuevo')) $('#formNuevo').nro_socio.value = data.proximo_nro_socio;
  renderSocios();
  renderSociosCrud();
}

async function cargarSociosCrud() {
  const q = encodeURIComponent($('#buscarSocioCrud').value.trim());
  const modo = modoBusquedaSocio('#buscarSocioCrudTodos');
  const data = await api(`/api/socios?q=${q}&modo_busqueda=${modo}`);
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

async function cargarControlGeneracion() {
  const form = $('#formGenerar');
  if (!form || !form.periodo.value) return null;
  const data = await api(`/api/cuotas/generar/control?periodo=${encodeURIComponent(form.periodo.value)}`);
  renderControlGeneracion(data.control);
  return data.control;
}

function renderControlGeneracion(control) {
  const box = $('#generarControl');
  if (!box || !control) return;
  const estado = control.puede_generar ? 'ok' : (control.forzable ? 'warning' : 'blocked');
  box.innerHTML = `
    <strong>${control.puede_generar ? 'Listo para generar' : (control.forzable ? 'Advertencia: se puede forzar' : 'No se puede generar')}</strong>
    <span>Periodo: ${control.periodo}</span>
    <span>Periodo anterior requerido: ${control.periodo_anterior} (${number(control.cuotas_anterior)} de ${number(control.socios_anterior_objetivo)} esperadas)</span>
    <span>Socios alcanzados: ${number(control.socios_objetivo)}</span>
    <span>Cuotas ya existentes: ${number(control.cuotas_periodo)}</span>
    <span>Cuotas estimadas a crear: ${number(control.faltantes_estimadas)}</span>
    ${control.motivo ? `<small>${control.motivo}</small>` : ''}
  `;
  box.className = `generation-control ${estado}`;
  prepararFiltroFaltantes(control);
}

function prepararFiltroFaltantes(control) {
  const form = $('#formFaltantesCuotas');
  if (!form || !control) return;
  if (!form.hasta.value) form.hasta.value = control.periodo_anterior || sumarMesesPeriodo(control.periodo, -1);
  if (!form.desde.value) form.desde.value = `${form.hasta.value.slice(0, 4)}-01`;
}

async function cargarFaltantesCuotas() {
  const form = $('#formFaltantesCuotas');
  if (!form) return;
  if (!form.hasta.value) {
    const control = await cargarControlGeneracion();
    if (control) prepararFiltroFaltantes(control);
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(formData(form))) {
    if (value) params.set(key, value);
  }
  const data = await api(`/api/cuotas/generar/faltantes?${params.toString()}`);
  state.faltantesCuotas = data;
  renderFaltantesCuotas();
}

function renderFaltantesCuotas() {
  const box = $('#faltantesResumen');
  const body = $('#faltantesCuotasBody');
  const data = state.faltantesCuotas;
  if (!box || !body || !data) return;
  const resumen = (data.resumen || []).slice(0, 8)
    .map(item => `<span>${item.periodo}: ${number(item.faltantes)} faltante(s)</span>`)
    .join('');
  box.className = `generation-control ${data.total ? 'warning' : 'ok'}`;
  box.innerHTML = `
    <strong>${data.total ? 'Hay cuotas sin generar' : 'No hay faltantes en el rango'}</strong>
    <span>Rango: ${data.desde || '-'} a ${data.hasta || '-'}</span>
    <span>Total faltantes: ${number(data.total || 0)} | Mostrados: ${number(data.mostrados || 0)}</span>
    ${resumen || '<span>Sin periodos incompletos para mostrar.</span>'}
    ${(data.total || 0) > (data.mostrados || 0) ? '<small>El listado esta limitado. Ajuste el rango o aumente el limite para ver mas.</small>' : ''}
  `;
  body.innerHTML = '';
  const rows = data.faltantes || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5">No hay cuotas faltantes para el rango seleccionado.</td></tr>';
    return;
  }
  for (const item of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.periodo}</td>
      <td>${item.nro_socio}</td>
      <td>${item.apellido}, ${item.nombre}<br><small>DNI ${item.dni || '-'}</small></td>
      <td>${item.cobrador} - ${cobradorTexto(item.cobrador)}</td>
      <td>${item.telefono || '-'}</td>
    `;
    body.appendChild(tr);
  }
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
      <td>${number(socio.cuotas_debe)}</td>
      <td>${number(socio.cuotas_adelantadas)}</td>
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
    <span>Debe ${number(socio.cuotas_debe)} cuota(s) | Adelantadas ${number(socio.cuotas_adelantadas)}</span>
  `;
  state.socioCrudCuotas = data.cuotas || [];
  cuotasSeleccionadasSocio = new Set();
  $('#socioCuotasToolbar').hidden = false;
  if (!$('#socioPagoFecha').value) $('#socioPagoFecha').value = fechaActual();
  renderCuotasSocioCrud();
  $('#btnSocioBajaCrud').disabled = false;
  $('#btnSocioEditarCrud').disabled = false;
  renderSociosCrud();
}

function cuotasSocioFiltradas() {
  const filtro = state.socioCuotasFiltro || 'pendiente';
  if (filtro === 'todas') return state.socioCrudCuotas;
  return state.socioCrudCuotas.filter(cuota => cuota.estado === filtro);
}

function actualizarResumenPagoSocio() {
  const seleccionadas = state.socioCrudCuotas.filter(cuota => cuotasSeleccionadasSocio.has(Number(cuota.id)));
  const total = seleccionadas.reduce((acc, cuota) => acc + Number(cuota.monto || 0), 0);
  const pendientes = state.socioCrudCuotas.filter(cuota => cuota.estado === 'pendiente');
  const pagadas = state.socioCrudCuotas.filter(cuota => cuota.estado === 'pagada');
  $('#socioPagoTotal').textContent = money(total);
  $('#btnPagarCuotasSocio').disabled = seleccionadas.length === 0;
  $('#socioCuotasResumen').textContent =
    `${number(pendientes.length)} impaga(s), ${number(pagadas.length)} paga(s). Seleccionadas ${number(seleccionadas.length)} por ${money(total)}.`;
}

function renderCuotasSocioCrud() {
  const box = $('#socioCrudCuotas');
  const cuotas = cuotasSocioFiltradas();
  box.innerHTML = '';
  document.querySelectorAll('[data-socio-cuotas-filter]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.socioCuotasFilter === state.socioCuotasFiltro);
  });
  if (!cuotas.length) {
    box.innerHTML = '<div class="empty">Este socio no tiene cuotas.</div>';
    actualizarResumenPagoSocio();
    return;
  }
  for (const cuota of cuotas) {
    const item = document.createElement('div');
    item.className = `cuota ${cuota.estado}`;
    const pendiente = cuota.estado === 'pendiente';
    const checked = cuotasSeleccionadasSocio.has(Number(cuota.id)) ? 'checked' : '';
    item.innerHTML = `
      <div class="dues-check">
        ${pendiente ? `<input type="checkbox" data-select-cuota-socio="${cuota.id}" ${checked}>` : '<span></span>'}
        <div>
          <strong>${cuota.periodo}</strong> - ${money(cuota.monto)} - ${cuota.estado}
          <small>${cuota.fecha_pago ? `Pagada el ${cuota.fecha_pago}` : 'Impaga / pendiente'}</small>
        </div>
      </div>
    `;
    box.appendChild(item);
  }
  box.querySelectorAll('[data-select-cuota-socio]').forEach(input => {
    input.addEventListener('change', () => {
      const id = Number(input.dataset.selectCuotaSocio);
      if (input.checked) cuotasSeleccionadasSocio.add(id);
      else cuotasSeleccionadasSocio.delete(id);
      actualizarResumenPagoSocio();
    });
  });
  actualizarResumenPagoSocio();
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
  $('#detalleMeta').textContent = `${socio.direccion} | Debe ${number(socio.cuotas_debe)} cuota(s) | Adelantadas ${number(socio.cuotas_adelantadas)}`;

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
        <strong>${cuota.periodo}</strong> - ${money(cuota.monto)} - ${cuota.estado}
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
      if ($('#paginaCaja') && !$('#paginaCaja').hidden) {
        await cargarCaja();
        await cargarCajaListado();
      }
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
      if ($('#paginaCaja') && !$('#paginaCaja').hidden) {
        await cargarCaja();
        await cargarCajaListado();
      }
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
      <td>${money(cuota.monto)}</td>
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
  $('#cuotasTotal').textContent = number(total);
  $('#cuotasPendientes').textContent = number(pendientes.length);
  $('#cuotasPagadas').textContent = number(pagadas.length);
  $('#cuotasMontoPendiente').textContent = money(montoPendiente);
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
      <td>${number(socio.cuotas_impagas)}</td>
      <td>${money(socio.deuda)}</td>
    `;
    body.appendChild(tr);
  }
}

function socioPagoTexto(socio) {
  return `#${socio.nro_socio} ${socio.apellido}, ${socio.nombre} - DNI ${socio.dni || '-'}`;
}

function seleccionarSocioPagoAdelantado(socio) {
  const form = $('#formPagoAdelantado');
  if (!form || !socio) return;
  form.socio_id.value = socio.id;
  $('#pagoAdelantadoSocioBuscar').value = socioPagoTexto(socio);
  $('#pagoAdelantadoSocioSeleccionado').textContent = socioPagoTexto(socio);
  $('#pagoAdelantadoSocioSeleccionado').classList.add('ready');
  $('#pagoAdelantadoSocioResultados').innerHTML = '';
}

function renderResultadosSocioPago(socios, mensaje = '') {
  const body = $('#pagoAdelantadoSocioResultados');
  if (!body) return;
  body.innerHTML = '';
  if (mensaje) {
    body.innerHTML = `<div class="member-results-note">${mensaje}</div>`;
    return;
  }
  if (!socios.length) {
    body.innerHTML = '<div class="member-results-note">No se encontraron socios.</div>';
    return;
  }
  for (const socio of socios.slice(0, 20)) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'member-result';
    btn.innerHTML = `
      <strong>${socio.apellido}, ${socio.nombre}</strong>
      <span>#${socio.nro_socio} | DNI ${socio.dni || '-'} | ${socio.telefono || 'Sin telefono'}</span>
    `;
    btn.addEventListener('click', () => seleccionarSocioPagoAdelantado(socio));
    body.appendChild(btn);
  }
}

async function buscarSociosPagoAdelantado() {
  const input = $('#pagoAdelantadoSocioBuscar');
  const form = $('#formPagoAdelantado');
  if (!input || !form) return;
  const q = input.value.trim();
  form.socio_id.value = '';
  $('#pagoAdelantadoSocioSeleccionado').textContent = 'Seleccione un socio.';
  $('#pagoAdelantadoSocioSeleccionado').classList.remove('ready');
  const modo = modoBusquedaSocio('#pagoAdelantadoSocioBuscarTodos');
  const minimo = modo === 'todos' ? 2 : 1;
  if (q.length < minimo) {
    renderResultadosSocioPago([], `Escriba al menos ${minimo} caracter${minimo === 1 ? '' : 'es'} para buscar.`);
    return;
  }
  const data = await api(`/api/socios?q=${encodeURIComponent(q)}&modo_busqueda=${modo}`);
  renderResultadosSocioPago(data.socios || []);
}

function abrirPagoAdelantado() {
  const form = $('#formPagoAdelantado');
  form.reset();
  form.socio_id.value = '';
  $('#pagoAdelantadoSocioBuscar').value = '';
  $('#pagoAdelantadoSocioSeleccionado').textContent = 'Seleccione un socio.';
  $('#pagoAdelantadoSocioSeleccionado').classList.remove('ready');
  renderResultadosSocioPago([], 'Busque por nro. de socio. Active la busqueda amplia para nombre, DNI, direccion, telefono o correo.');
  const selected = state.socioCrudId || state.selectedId;
  if (selected) {
    const socio = state.socios.find(item => Number(item.id) === Number(selected));
    if (socio) seleccionarSocioPagoAdelantado(socio);
  }
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

async function cargarCajaListado() {
  const form = $('#formCajaListado');
  if (!form) return;
  const desde = form.desde.value || fechaHace(30);
  const hasta = form.hasta.value || fechaActual();
  const data = await api(`/api/caja/listado?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}`);
  state.cajaListado = {
    dias: data.dias,
    resumen: data.resumen
  };
  renderCajaListado();
}

function renderCaja() {
  const form = $('#formCajaDia');
  if (!form || !state.caja.dia) return;
  form.fecha.value = state.caja.dia.fecha;
  form.saldo_inicial.value = decimalInput(state.caja.dia.saldo_inicial);
  form.observacion.value = state.caja.dia.observacion || '';
  form.cerrado.checked = Number(state.caja.dia.cerrado) === 1;
  $('#cajaSaldoInicial').textContent = money(state.caja.resumen.saldo_inicial);
  $('#cajaIngresos').textContent = money(state.caja.resumen.ingresos);
  $('#cajaEgresos').textContent = money(state.caja.resumen.egresos);
  $('#cajaSaldoFinal').textContent = money(state.caja.resumen.saldo_final);
  $('#cajaCantidad').textContent = `${number(state.caja.resumen.cantidad_movimientos)} movimiento(s) de efectivo del dia.`;

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
      await cargarCajaListado();
      toast('Movimiento eliminado');
    });
  });
}

function renderCajaListado() {
  const body = $('#cajaListadoBody');
  if (!body) return;
  const resumen = state.cajaListado.resumen || {};
  $('#cajaListadoIngresos').textContent = money(resumen.ingresos);
  $('#cajaListadoEgresos').textContent = money(resumen.egresos);
  $('#cajaListadoNeto').textContent = money(resumen.neto);
  $('#cajaListadoDias').textContent = number(resumen.dias || 0);
  body.innerHTML = '';
  if (!state.cajaListado.dias.length) {
    body.innerHTML = '<tr><td colspan="7">No hay dias de caja cargados para este rango.</td></tr>';
    return;
  }
  for (const dia of state.cajaListado.dias) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${dia.fecha}</td>
      <td>${money(dia.saldo_inicial)}</td>
      <td>${money(dia.ingresos)}</td>
      <td>${money(dia.egresos)}</td>
      <td><strong>${money(dia.saldo_final)}</strong></td>
      <td>${number(dia.movimientos)}</td>
      <td>${Number(dia.cerrado) === 1 ? 'Cerrada' : 'Abierta'}</td>
    `;
    tr.addEventListener('click', async () => {
      $('#formCajaDia').fecha.value = dia.fecha;
      await cargarCaja();
      enfocar('#formCajaDia');
    });
    body.appendChild(tr);
  }
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
    form.monto.value = decimalInput(movimiento.monto);
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
  form.monto.value = decimalInput(cuota.monto);
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
  state.socioCrudCuotas = [];
  cuotasSeleccionadasSocio = new Set();
  $('#socioCuotasToolbar').hidden = true;
  $('#btnSocioBajaCrud').disabled = true;
  $('#btnSocioEditarCrud').disabled = true;
  $('#socioCrudTitulo').textContent = 'Seleccione un socio';
  $('#socioCrudMeta').textContent = 'Click sobre un socio para ver sus cuotas pagas e impagas.';
  $('#socioCrudContacto').innerHTML = '';
  $('#socioCrudCuotas').innerHTML = '';
  cargarSociosCrud();
}

function mostrarPaginaCuotas(vista = 'admin') {
  $('#paginaInicio').hidden = true;
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = false;
  $('#paginaConfig').hidden = true;
  $('#paginaCaja').hidden = true;
  mostrarCuotasHoja(vista);
  cargarCuotas();
  cargarMorosos();
}

function mostrarCuotasHoja(vista = 'admin') {
  const views = new Set(['admin', 'generar', 'impresion', 'morosos']);
  const selected = views.has(vista) ? vista : 'admin';
  document.querySelectorAll('[data-cuotas-panel]').forEach(panel => {
    panel.hidden = panel.dataset.cuotasPanel !== selected;
  });
  document.querySelectorAll('[data-cuotas-view]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.cuotasView === selected);
  });
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

function cerrarMenus() {
  document.querySelectorAll('.nav-menu[open]').forEach(menu => {
    menu.removeAttribute('open');
  });
}

function enfocar(selector) {
  const el = $(selector);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (typeof el.focus === 'function') el.focus({ preventScroll: true });
}

function navegar(action) {
  cerrarMenus();
  if (action === 'inicio' || action === 'reporte-dashboard') {
    mostrarPaginaInicio();
    return;
  }
  if (action === 'socios') {
    mostrarPaginaSocios();
    return;
  }
  if (action === 'socio-nuevo') {
    mostrarPaginaSocios();
    setTimeout(() => abrirModalSocio(), 120);
    return;
  }
  if (action === 'cuotas') {
    mostrarPaginaCuotas('admin');
    return;
  }
  if (action === 'cuotas-generar') {
    mostrarPaginaCuotas('generar');
    setTimeout(async () => {
      await cargarControlGeneracion();
      enfocar('#formGenerar input[name="periodo"]');
    }, 120);
    return;
  }
  if (action === 'pago-adelantado') {
    mostrarPaginaCuotas('admin');
    setTimeout(() => abrirPagoAdelantado(), 180);
    return;
  }
  if (action === 'imprimir-cuotas') {
    mostrarPaginaCuotas('impresion');
    setTimeout(() => enfocar('#formImprimir input[name="periodo"]'), 120);
    return;
  }
  if (action === 'morosos' || action === 'reporte-morosos') {
    mostrarPaginaCuotas('morosos');
    setTimeout(() => enfocar('#morososBody'), 160);
    return;
  }
  if (action === 'caja' || action === 'reporte-caja') {
    mostrarPaginaCaja();
    setTimeout(() => enfocar(action === 'reporte-caja' ? '.caja-summary' : '#formCajaDia'), 160);
    return;
  }
  if (action === 'caja-listado' || action === 'reporte-caja-listado') {
    mostrarPaginaCaja();
    setTimeout(() => enfocar('.caja-daily-list'), 160);
    return;
  }
  if (action === 'caja-ingreso') {
    mostrarPaginaCaja();
    setTimeout(() => abrirMovimientoCaja('ingreso'), 180);
    return;
  }
  if (action === 'caja-egreso') {
    mostrarPaginaCaja();
    setTimeout(() => abrirMovimientoCaja('egreso'), 180);
    return;
  }
  if (action === 'caja-movimientos') {
    mostrarPaginaCaja();
    setTimeout(() => enfocar('#cajaMovimientosBody'), 160);
    return;
  }
  if (action === 'config') {
    mostrarPaginaConfig();
    return;
  }
  if (action === 'config-seguridad') {
    mostrarPaginaConfig();
    setTimeout(() => enfocar('#formSeguridad'), 160);
    return;
  }
  if (action === 'manual') {
    window.open('/manual_usuario.html', '_blank');
  }
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
  configurarAcceso();
  const sesion = await obtenerSesion();
  if (!sesion.autenticado) {
    mostrarLogin();
    return;
  }
  state.usuario = sesion.usuario || '';
  mostrarSistema();
  await cargarConfig();
  const periodo = periodoDefault();
  $('#formDashboard').periodo.value = periodo;
  $('#formGenerar').periodo.value = periodo;
  $('#formImprimir').periodo.value = periodo;
  $('#formImprimir').cobrador.value = state.config.impresion_cobrador_default || '1';
  $('#formFaltantesCuotas').hasta.value = sumarMesesPeriodo(periodo, -1);
  $('#formFaltantesCuotas').desde.value = `${$('#formFaltantesCuotas').hasta.value.slice(0, 4)}-01`;
  if ($('#formCuota')) $('#formCuota').periodo.value = periodo;
  $('#formFiltroCuotas').periodo.value = periodo;
  $('#formCajaDia').fecha.value = fechaActual();
  $('#formCajaListado').desde.value = fechaHace(30);
  $('#formCajaListado').hasta.value = fechaActual();
  actualizarModoBusquedaSocio('#buscarSocioCrud', '#buscarSocioCrudTodos');
  actualizarModoBusquedaSocio('#pagoAdelantadoSocioBuscar', '#pagoAdelantadoSocioBuscarTodos');

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

  document.querySelectorAll('[data-nav]').forEach(btn => {
    btn.addEventListener('click', () => navegar(btn.dataset.nav));
  });
  document.querySelectorAll('[data-cuotas-view]').forEach(btn => {
    btn.addEventListener('click', () => mostrarCuotasHoja(btn.dataset.cuotasView));
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.app-nav')) cerrarMenus();
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
  $('#buscarSocioCrudTodos').addEventListener('change', () => {
    actualizarModoBusquedaSocio('#buscarSocioCrud', '#buscarSocioCrudTodos');
    cargarSociosCrud().catch(error => toast(error.message));
  });
  $('#btnSocioNuevoModo').addEventListener('click', () => abrirModalSocio());
  $('#btnSocioEditarCrud').addEventListener('click', () => {
    if (state.socioCrudId) abrirModalSocio(state.socioCrudId);
  });
  document.querySelectorAll('[data-socio-cuotas-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.socioCuotasFiltro = btn.dataset.socioCuotasFilter;
      renderCuotasSocioCrud();
    });
  });
  $('#btnPagarCuotasSocio').addEventListener('click', () => {
    pagarCuotasSocioSeleccionadas().catch(error => toast(error.message));
  });
  $('#btnCajaIngreso').addEventListener('click', () => abrirMovimientoCaja('ingreso'));
  $('#btnCajaEgreso').addEventListener('click', () => abrirMovimientoCaja('egreso'));
  $('#btnCajaActualizar').addEventListener('click', cargarCaja);
  $('#btnPagoAdelantado').addEventListener('click', abrirPagoAdelantado);
  $('#pagoAdelantadoSocioBuscar').addEventListener('input', () => {
    clearTimeout(pagoAdelantadoSearchTimer);
    pagoAdelantadoSearchTimer = setTimeout(() => {
      buscarSociosPagoAdelantado().catch(error => toast(error.message));
    }, 250);
  });
  $('#pagoAdelantadoSocioBuscarTodos').addEventListener('change', () => {
    actualizarModoBusquedaSocio('#pagoAdelantadoSocioBuscar', '#pagoAdelantadoSocioBuscarTodos');
    buscarSociosPagoAdelantado().catch(error => toast(error.message));
  });
  $('#btnActualizarMorosos').addEventListener('click', cargarMorosos);
  $('#btnImprimirMorosos').addEventListener('click', () => window.open('/imprimir-morosos', '_blank'));
  $('#formCajaDia').fecha.addEventListener('change', cargarCaja);
  $('#formGenerar').periodo.addEventListener('change', async () => {
    const control = await cargarControlGeneracion();
    if (control) {
      $('#formFaltantesCuotas').hasta.value = control.periodo_anterior;
      $('#formFaltantesCuotas').desde.value = `${control.periodo_anterior.slice(0, 4)}-01`;
    }
  });
  $('#btnActualizarFaltantes').addEventListener('click', () => cargarFaltantesCuotas().catch(error => toast(error.message)));
  $('#formFaltantesCuotas').addEventListener('submit', async (event) => {
    event.preventDefault();
    await cargarFaltantesCuotas();
  });
  $('#formCajaListado').addEventListener('submit', async (event) => {
    event.preventDefault();
    await cargarCajaListado();
  });
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
  $('#modalAdminClave').addEventListener('cancel', () => {
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
    const control = await cargarControlGeneracion();
    if (!control) {
      throw new Error('Revise el periodo antes de generar cuotas.');
    }
    if (!control.puede_generar && !control.forzable) {
      throw new Error((control && control.motivo) || 'Revise el periodo antes de generar cuotas.');
    }
    data.forzar = !control.puede_generar && control.forzable;
    const mensaje =
      `${data.forzar ? 'Va a FORZAR la generacion' : 'Va a generar cuotas'} para ${control.periodo}.\n\n` +
      `Periodo anterior requerido: ${control.periodo_anterior} (${number(control.cuotas_anterior)} de ${number(control.socios_anterior_objetivo)} esperadas)\n` +
      `Socios alcanzados: ${number(control.socios_objetivo)}\n` +
      `Cuotas ya existentes en el periodo: ${number(control.cuotas_periodo)}\n` +
      `Cuotas estimadas a crear: ${number(control.faltantes_estimadas)}\n\n` +
      `${data.forzar ? 'Hay meses anteriores incompletos. Esta accion pedira clave de administrador.\n\n' : ''}` +
      'Confirma la generacion?';
    if (!confirm(mensaje)) return;
    const request = { method: 'POST', body: JSON.stringify(data) };
    const result = data.forzar
      ? await apiAdmin('/api/cuotas/generar', request, `Autorizar generacion forzada de ${control.periodo}.`)
      : await api('/api/cuotas/generar', request);
    $('#formFiltroCuotas').periodo.value = result.periodo;
    await refrescarTodo();
    await cargarControlGeneracion();
    await cargarFaltantesCuotas();
    toast(`${result.forzada ? 'Generacion forzada' : 'Generacion'}: ${number(result.cuotas_creadas)} cuota(s) para ${result.periodo}`);
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
      await apiConClaveSiHaceFalta('/api/caja/dia', request, 'Autorizar modificacion de caja cerrada.');
    }
    await cargarCaja();
    await cargarCajaListado();
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

  $('#formAcceso').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    if (data.clave_nueva !== data.clave_repetida) {
      toast('La nueva contrasena no coincide');
      return;
    }
    await apiAdmin(
      '/api/config/acceso',
      { method: 'POST', body: JSON.stringify(data) },
      'Autorizar cambio de acceso al sistema.'
    );
    event.currentTarget.reset();
    toast('Usuario y contrasena de ingreso actualizados');
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
        await apiConClaveSiHaceFalta('/api/caja/movimientos', request, 'Autorizar movimiento en caja cerrada.');
      }
      toast('Movimiento cargado');
    }
    cerrarDialogs();
    await cargarCaja();
    await cargarCajaListado();
  });

  $('#formPagoAdelantado').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    if (!data.socio_id) {
      toast('Seleccione un socio para el pago adelantado');
      return;
    }
    const request = { method: 'POST', body: JSON.stringify(data) };
    const result = await apiConClaveSiHaceFalta('/api/cuotas/adelanto', request, 'Autorizar pago adelantado en caja cerrada.');
    cerrarDialogs();
    await refrescarTodo();
    const cajaMsg = data.medio_pago === 'efectivo' ? ' Ingreso registrado en caja.' : ' No mueve caja diaria.';
    toast(`Pago adelantado: ${number(result.cuotas_pagadas)} cuota(s) pagada(s).${cajaMsg}`);
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
  await cargarCajaListado();
  await cargarControlGeneracion();
}

init().catch(error => toast(error.message));
