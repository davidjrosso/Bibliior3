const state = {
  socios: [],
  cuotas: [],
  selectedId: null,
  socioCrudId: null,
  config: {}
};

const $ = (selector) => document.querySelector(selector);

function periodoSiguiente() {
  const now = new Date();
  const year = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();
  const month = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  return `${year}-${String(month).padStart(2, '0')}`;
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

function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 2600);
}

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
  form.estado.value = 'activo';
  form.cobrador.value = '1';
  state.socioCrudId = null;
  $('#socioFormTitulo').textContent = 'Nuevo socio';
}

async function cargarConfig() {
  const data = await api('/api/config');
  state.config = data.config;
  $('#formConfig').monto_activo.value = state.config.monto_activo || 0;
  $('#formConfig').monto_jubilado.value = state.config.monto_jubilado || 0;
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
      <td>${socio.estado}</td>
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
  for (const field of ['nro_socio', 'dni', 'apellido', 'nombre', 'telefono', 'email', 'direccion', 'barrio', 'localidad', 'fecha_nacimiento', 'ocupacion', 'estado', 'cobrador']) {
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
  for (const field of ['nro_socio', 'dni', 'apellido', 'nombre', 'telefono', 'email', 'direccion', 'barrio', 'localidad', 'fecha_nacimiento', 'ocupacion', 'estado', 'cobrador']) {
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
      await api(`/api/cuotas/${btn.dataset.pagar}/pagar`, { method: 'POST', body: '{}' });
      await seleccionarSocio(state.selectedId);
      await cargarSocios();
    });
  });
  box.querySelectorAll('[data-pendiente]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await api(`/api/cuotas/${btn.dataset.pendiente}/pendiente`, { method: 'POST', body: '{}' });
      await seleccionarSocio(state.selectedId);
      await cargarSocios();
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
      await api(`/api/cuotas/${btn.dataset.pagarCuota}/pagar`, { method: 'POST', body: '{}' });
      await refrescarTodo();
      toast('Cuota marcada como pagada');
    });
  });
  body.querySelectorAll('[data-pendiente-cuota]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await api(`/api/cuotas/${btn.dataset.pendienteCuota}/pendiente`, { method: 'POST', body: '{}' });
      await refrescarTodo();
      toast('Cuota marcada como pendiente');
    });
  });
  body.querySelectorAll('[data-delete-cuota]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Eliminar esta cuota?')) return;
      await api(`/api/cuotas/${btn.dataset.deleteCuota}`, { method: 'DELETE' });
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
  cargarCuotas();
}

function mostrarPaginaInicio() {
  $('#paginaSocios').hidden = true;
  $('#paginaCuotas').hidden = true;
  $('#paginaInicio').hidden = false;
  resetNuevoSocio();
}

function imprimirCuotas(cobrador) {
  const periodo = $('#formFiltroCuotas').periodo.value || $('#formImprimir').periodo.value || periodoSiguiente();
  window.open(`/imprimir?periodo=${encodeURIComponent(periodo)}&cobrador=${cobrador}`, '_blank');
}

function cerrarDialogs() {
  document.querySelectorAll('dialog').forEach(d => d.close());
}

async function init() {
  $('#formDashboard').periodo.value = periodoSiguiente();
  $('#formGenerar').periodo.value = periodoSiguiente();
  $('#formImprimir').periodo.value = periodoSiguiente();
  if ($('#formCuota')) $('#formCuota').periodo.value = periodoSiguiente();
  $('#formFiltroCuotas').periodo.value = periodoSiguiente();

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
  $('#btnVolverInicio').addEventListener('click', mostrarPaginaInicio);
  $('#btnVolverInicioCuotas').addEventListener('click', mostrarPaginaInicio);
  $('#btnConfig').addEventListener('click', () => abrir($('#modalConfig')));
  document.querySelectorAll('[data-close]').forEach(btn => btn.addEventListener('click', cerrarDialogs));
  $('#btnBuscarSocioCrud').addEventListener('click', cargarSociosCrud);
  $('#buscarSocioCrud').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') cargarSociosCrud();
  });
  $('#btnSocioNuevoModo').addEventListener('click', () => abrirModalSocio());
  $('#btnSocioEditarCrud').addEventListener('click', () => {
    if (state.socioCrudId) abrirModalSocio(state.socioCrudId);
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
    const result = await api(`/api/socios/${state.socioCrudId}`, { method: 'DELETE' });
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
      const result = await api(`/api/socios/${state.selectedId}`, { method: 'DELETE' });
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

  $('#btnPrintCobrador').addEventListener('click', () => imprimirCuotas(1));
  $('#btnPrintBiblioteca').addEventListener('click', () => imprimirCuotas(3));

  $('#formConfig').addEventListener('submit', async (event) => {
    event.preventDefault();
    await api('/api/config', { method: 'POST', body: JSON.stringify(formData(event.currentTarget)) });
    await cargarConfig();
    cerrarDialogs();
    toast('Importes guardados');
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
    await api(`/api/cuotas/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    cerrarDialogs();
    await refrescarTodo();
    toast('Cuota modificada');
  });

  await cargarConfig();
  await cargarDashboard();
  await cargarSocios();
  await cargarCuotas();
}

init().catch(error => toast(error.message));
