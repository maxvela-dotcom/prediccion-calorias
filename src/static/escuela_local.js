/*
 * Capa de datos LOCAL del módulo Escuela (Willys_IA).
 *
 * Ejecuta las MISMAS reglas RN-E01 a RN-E07 del servicio Python, pero usando
 * IndexedDB (base de datos del navegador) en lugar de SQLite. Así el celular
 * guarda asistencias, avisos y cobros sin depender del servidor.
 *
 * Expone window.API_LOCAL con:
 *   - soporta(ruta) : bool
 *   - llamar(ruta, opciones) : Promise -> mismo JSON que /api/escuela
 *   - qrDataURL(token) : string (PNG del QR)
 *   - reiniciarDemo() : borra la base local y recarga
 */
(function (global) {
  "use strict";

  const DB_NAME = "escuela_futbol_local";
  const DB_VERSION = 1;
  const STORES = [
    "sedes", "categorias", "estudiantes", "sesiones",
    "asistencias", "avisos", "pagos", "meta"
  ];

  let promesaDB = null;
  let promesaSiembra = null;

  const NOMBRES = [
    "Mateo Quispe", "Santiago Mamani", "Thiago Flores", "Lucas Choque",
    "Benjamín Rojas", "Dylan Condori", "Joaquín Vargas", "Samuel Apaza",
    "Gabriel Ticona", "Ian Colque", "Adrián Huanca", "Diego Céspedes",
    "Camila Cruz", "Valentina Lima", "Antonella Paz", "Briana Soliz",
    "Danna Arce", "Micaela Torrez", "Renata Aguilar", "Luana Zeballos",
    "Fernanda Orellana", "Jazmín Ferrufino", "Nicole Bustillos", "Ariana Valdez"
  ];

  const PROFESORES = [
    "Prof. Ramiro Salazar", "Prof. Lucía Paredes", "Prof. Marco Villarroel",
    "Prof. Andrea Ferrufino", "Prof. Javier Copa", "Prof. Paola Sánchez"
  ];

  // -------------------------------------------------------------------
  // IndexedDB: operaciones mínimas (sin reglas de negocio aquí)
  // -------------------------------------------------------------------

  function abrirDB() {
    if (promesaDB) return promesaDB;
    promesaDB = new Promise((resolve, reject) => {
      const peticion = indexedDB.open(DB_NAME, DB_VERSION);
      peticion.onupgradeneeded = () => {
        const db = peticion.result;
        STORES.forEach((nombre) => {
          if (!db.objectStoreNames.contains(nombre)) {
            if (nombre === "meta") {
              db.createObjectStore(nombre, { keyPath: "key" });
            } else {
              const store = db.createObjectStore(nombre, { keyPath: "id" });
              if (nombre === "asistencias" || nombre === "avisos") {
                store.createIndex("sesion_estudiante", ["sesion_id", "estudiante_id"], { unique: true });
              }
              if (nombre === "pagos") {
                store.createIndex("estudiante_periodo", ["estudiante_id", "periodo"], { unique: true });
              }
            }
          }
        });
      };
      peticion.onsuccess = () => resolve(peticion.result);
      peticion.onerror = () => reject(peticion.error || new Error("No se pudo abrir la base local."));
    });
    return promesaDB;
  }

  function getAll(nombre) {
    return abrirDB().then((db) => new Promise((resolve, reject) => {
      const transaccion = db.transaction(nombre, "readonly");
      const peticion = transaccion.objectStore(nombre).getAll();
      let resultado = [];
      peticion.onsuccess = () => { resultado = peticion.result || []; };
      transaccion.oncomplete = () => resolve(resultado);
      transaccion.onerror = () => reject(transaccion.error);
    }));
  }

  function get(nombre, clave) {
    return abrirDB().then((db) => new Promise((resolve, reject) => {
      const transaccion = db.transaction(nombre, "readonly");
      const peticion = transaccion.objectStore(nombre).get(clave);
      let resultado = null;
      peticion.onsuccess = () => { resultado = peticion.result || null; };
      transaccion.oncomplete = () => resolve(resultado);
      transaccion.onerror = () => reject(transaccion.error);
    }));
  }

  function put(nombre, objeto) {
    return abrirDB().then((db) => new Promise((resolve, reject) => {
      const transaccion = db.transaction(nombre, "readwrite");
      const peticion = transaccion.objectStore(nombre).put(objeto);
      peticion.onsuccess = () => { if (objeto.id === undefined) objeto.id = peticion.result; };
      transaccion.oncomplete = () => resolve(objeto);
      transaccion.onerror = () => reject(transaccion.error || new Error("No se pudo guardar."));
      transaccion.onabort = () => reject(transaccion.error || new Error("Transacción cancelada."));
    }));
  }

  function vaciar(nombre) {
    return abrirDB().then((db) => new Promise((resolve, reject) => {
      const transaccion = db.transaction(nombre, "readwrite");
      transaccion.objectStore(nombre).clear();
      transaccion.oncomplete = () => resolve();
      transaccion.onerror = () => reject(transaccion.error);
    }));
  }

  function guardarTodo(datos, nombres) {
    let cadena = Promise.resolve();
    nombres.forEach((nombre) => {
      cadena = cadena.then(() => Promise.all((datos[nombre] || []).map((obj) => put(nombre, obj))));
    });
    return cadena;
  }

  async function cargarTodo() {
    const datos = {};
    for (const nombre of STORES) {
      if (nombre !== "meta") datos[nombre] = await getAll(nombre);
    }
    return datos;
  }

  // -------------------------------------------------------------------
  // Utilidades (equivalentes a las del servicio Python)
  // -------------------------------------------------------------------

  function ahora() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
           `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function hoy() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  function fechaMenos(offset) {
    const d = new Date();
    d.setDate(d.getDate() - offset);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  function periodoActual() {
    return hoy().slice(0, 7);
  }

  function validarPeriodo(periodo) {
    const limpio = String(periodo || "").trim();
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(limpio)) {
      throw new Error("El periodo debe tener formato AAAA-MM (ej. 2026-11).");
    }
    return limpio;
  }

  function validarFecha(fecha) {
    const limpio = String(fecha || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(limpio) || Number.isNaN(Date.parse(limpio))) {
      throw new Error("La fecha debe tener formato AAAA-MM-DD.");
    }
    return limpio;
  }

  function validarHora(hora) {
    const limpio = String(hora || "").trim();
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(limpio)) {
      throw new Error("La hora debe tener formato HH:MM.");
    }
    return limpio;
  }

  function entero(valor, campo) {
    const n = Number(valor);
    if (!Number.isInteger(n)) throw new Error(`El campo '${campo}' debe ser un número entero.`);
    return n;
  }

  function mapa(lista) {
    const m = new Map();
    (lista || []).forEach((x) => m.set(x.id, x));
    return m;
  }

  function siguienteId(lista) {
    return (lista || []).reduce((max, x) => Math.max(max, Number(x.id) || 0), 0) + 1;
  }

  function clon(valor) {
    return JSON.parse(JSON.stringify(valor));
  }

  // -------------------------------------------------------------------
  // DTO: mismas formas que devuelve la API de Flask
  // -------------------------------------------------------------------

  function sedeDTO(s) {
    return { id: s.id, nombre: s.nombre };
  }

  function categoriaDTO(c) {
    return { id: c.id, nombre: c.nombre, precio_mensual: Math.round(Number(c.precio_mensual) * 100) / 100 };
  }

  function estudianteDTO(e, d) {
    const cat = mapa(d.categorias).get(e.categoria_id) || {};
    const sede = mapa(d.sedes).get(e.sede_id) || {};
    return {
      id: e.id,
      nombre: e.nombre,
      categoria_id: e.categoria_id,
      categoria: cat.nombre || "",
      sede_id: e.sede_id,
      sede: sede.nombre || "",
      qr_token: e.qr_token,
      becado: Boolean(e.becado),
      estado: e.estado,
      precio_mensual: Math.round(Number(cat.precio_mensual || 0) * 100) / 100
    };
  }

  function sesionDTO(s, d) {
    const cat = mapa(d.categorias).get(s.categoria_id) || {};
    const sede = mapa(d.sedes).get(s.sede_id) || {};
    return {
      id: s.id,
      sede_id: s.sede_id,
      sede: sede.nombre || "",
      categoria_id: s.categoria_id,
      categoria: cat.nombre || "",
      fecha: s.fecha,
      hora: s.hora,
      entrenador: s.entrenador
    };
  }

  function avisoDTO(a, d) {
    const s = mapa(d.sesiones).get(a.sesion_id) || {};
    const e = mapa(d.estudiantes).get(a.estudiante_id) || {};
    const cat = mapa(d.categorias).get(s.categoria_id) || {};
    const sede = mapa(d.sedes).get(s.sede_id) || {};
    const dto = {
      id: a.id,
      sesion_id: a.sesion_id,
      estudiante_id: a.estudiante_id,
      estudiante: e.nombre || "",
      estado: a.estado,
      creada_en: a.creada_en,
      enviada_en: a.enviada_en || "",
      fecha: s.fecha || "",
      hora: s.hora || "",
      categoria: cat.nombre || "",
      sede: sede.nombre || ""
    };
    dto.mensaje =
      `El alumno ${dto.estudiante} faltó al entrenamiento del ` +
      `${dto.fecha} (${dto.categoria} · ${dto.sede}). ` +
      "Por favor, justifique la falta y solicite la recuperación.";
    return dto;
  }

  function cobroDTO(d, estudiante, periodo) {
    const sesionesId = new Set(
      d.sesiones.filter((s) => s.fecha.slice(0, 7) === periodo).map((s) => s.id)
    );
    const asistencias = d.asistencias.filter(
      (a) => a.estudiante_id === estudiante.id && sesionesId.has(a.sesion_id)
    ).length;

    let monto, motivo;
    if (estudiante.becado) {
      monto = 0; motivo = "BECA";
    } else if (asistencias === 0) {
      monto = 0; motivo = "SIN_ASISTENCIA";
    } else {
      const cat = mapa(d.categorias).get(estudiante.categoria_id) || {};
      monto = Number(cat.precio_mensual || 0); motivo = "ASISTENCIA";
    }

    const pago = d.pagos.find(
      (p) => p.estudiante_id === estudiante.id && p.periodo === periodo
    );
    let estadoPago, fechaPago = "";
    if (monto <= 0) {
      estadoPago = "NO_APLICA";
    } else if (pago) {
      estadoPago = pago.estado;
      fechaPago = pago.fecha_pago || "";
    } else {
      estadoPago = "PENDIENTE";
    }

    const dto = estudianteDTO(estudiante, d);
    return {
      estudiante_id: estudiante.id,
      nombre: dto.nombre,
      categoria: dto.categoria,
      sede: dto.sede,
      asistencias: asistencias,
      monto: Math.round(monto * 100) / 100,
      motivo: motivo,
      estado_pago: estadoPago,
      fecha_pago: fechaPago
    };
  }

  function resumenConDatos(d, periodo) {
    const cobros = listarCobrosConDatos(d, periodo);
    const sesionesHoy = d.sesiones.filter((s) => s.fecha === hoy());
    const idsHoy = new Set(sesionesHoy.map((s) => s.id));
    const asistenciasHoy = d.asistencias.filter((a) => idsHoy.has(a.sesion_id)).length;

    const presentesPorSesion = new Set(d.asistencias.map((a) => `${a.sesion_id}:${a.estudiante_id}`));
    let ausentesHoy = 0;
    sesionesHoy.forEach((s) => {
      d.estudiantes.forEach((e) => {
        if (e.estado === "ACTIVO" && e.sede_id === s.sede_id && e.categoria_id === s.categoria_id) {
          if (!presentesPorSesion.has(`${s.id}:${e.id}`)) ausentesHoy += 1;
        }
      });
    });

    return {
      periodo: periodo,
      estudiantes_activos: d.estudiantes.filter((e) => e.estado === "ACTIVO").length,
      sesiones_hoy: sesionesHoy.length,
      presentes_hoy: asistenciasHoy,
      ausentes_hoy: ausentesHoy,
      avisos_pendientes: d.avisos.filter((a) => a.estado === "PENDIENTE").length,
      total_pendiente: cobros.resumen.total_pendiente,
      total_cobrado: cobros.resumen.total_cobrado
    };
  }

  function listarCobrosConDatos(d, periodo) {
    const cobros = d.estudiantes
      .filter((e) => e.estado === "ACTIVO")
      .map((e) => cobroDTO(d, e, periodo));
    const red = (n) => Math.round(n * 100) / 100;
    return {
      periodo: periodo,
      cobros: cobros,
      resumen: {
        estudiantes: cobros.length,
        becados: cobros.filter((c) => c.motivo === "BECA").length,
        sin_asistencia: cobros.filter((c) => c.motivo === "SIN_ASISTENCIA").length,
        pagados: cobros.filter((c) => c.estado_pago === "PAGADO").length,
        pendientes: cobros.filter((c) => c.estado_pago === "PENDIENTE").length,
        total_facturado: red(cobros.reduce((s, c) => s + c.monto, 0)),
        total_cobrado: red(cobros.filter((c) => c.estado_pago === "PAGADO").reduce((s, c) => s + c.monto, 0)),
        total_pendiente: red(cobros.filter((c) => c.estado_pago === "PENDIENTE").reduce((s, c) => s + c.monto, 0))
      }
    };
  }

  // -------------------------------------------------------------------
  // Datos de demostración (idénticos a escuela_seed.py)
  // -------------------------------------------------------------------

  async function sembrarSiNecesario() {
    if (!promesaSiembra) {
      promesaSiembra = hacerSiembra().catch((err) => {
        promesaSiembra = null;
        throw err;
      });
    }
    return promesaSiembra;
  }

  async function hacerSiembra() {
    if (await get("meta", "sembrado")) return;

    for (const nombre of STORES) {
      if (nombre !== "meta") await vaciar(nombre);
    }

    const datos = {
      sedes: [
        { id: 1, nombre: "Sede Central" },
        { id: 2, nombre: "Sede Norte" }
      ],
      categorias: [
        { id: 1, nombre: "Sub-8", precio_mensual: 400 },
        { id: 2, nombre: "Sub-15", precio_mensual: 500 },
        { id: 3, nombre: "Sub-18", precio_mensual: 600 }
      ],
      estudiantes: [], sesiones: [], asistencias: [], avisos: [], pagos: []
    };

    let indiceNombre = 0;
    datos.sedes.forEach((sede) => {
      datos.categorias.forEach((categoria) => {
        for (let i = 0; i < 4; i += 1) {
          indiceNombre += 1;
          datos.estudiantes.push({
            id: indiceNombre,
            nombre: NOMBRES[(indiceNombre - 1) % NOMBRES.length],
            categoria_id: categoria.id,
            sede_id: sede.id,
            qr_token: "EF-" + String(indiceNombre).padStart(4, "0"),
            becado: indiceNombre === 6 || indiceNombre === 18 ? 1 : 0,
            estado: "ACTIVO",
            fecha_registro: ahora()
          });
        }
      });
    });

    let idSesion = 0;
    let idAsistencia = 0;
    let indiceProfesor = 0;
    datos.sedes.forEach((sede) => {
      datos.categorias.forEach((categoria) => {
        const grupo = datos.estudiantes.filter(
          (e) => e.sede_id === sede.id && e.categoria_id === categoria.id
        );
        const hora = sede.nombre === "Sede Central" ? "16:00" : "18:00";
        for (let offset = 0; offset <= 20; offset += 2) {
          indiceProfesor += 1;
          idSesion += 1;
          const sesion = {
            id: idSesion,
            sede_id: sede.id,
            categoria_id: categoria.id,
            fecha: fechaMenos(offset),
            hora: hora,
            entrenador: PROFESORES[(indiceProfesor - 1) % PROFESORES.length],
            creada_en: ahora()
          };
          datos.sesiones.push(sesion);
          grupo.forEach((estudiante) => {
            const ausente = offset === 0
              ? (estudiante.id % 4) === (sesion.id % 4)
              : ((estudiante.id + offset) % 6 === 0);
            if (!ausente) {
              idAsistencia += 1;
              datos.asistencias.push({
                id: idAsistencia,
                sesion_id: sesion.id,
                estudiante_id: estudiante.id,
                metodo: ((estudiante.id + offset) % 3) ? "QR" : "MANUAL",
                registrada_en: ahora()
              });
            }
          });
        }
      });
    });

    await guardarTodo(datos, ["sedes", "categorias", "estudiantes", "sesiones", "asistencias"]);
    await put("meta", { key: "sembrado", valor: true });
  }

  // -------------------------------------------------------------------
  // Casos de uso (reglas RN-E01 a RN-E07)
  // -------------------------------------------------------------------

  async function contexto(periodo) {
    const d = await cargarTodo();
    const per = validarPeriodo(periodo || periodoActual());
    const hoyTexto = hoy();
    const sesionesHoy = d.sesiones
      .filter((s) => s.fecha === hoyTexto)
      .sort((a, b) => b.hora.localeCompare(a.hora))
      .slice(0, 20)
      .map((s) => sesionDTO(s, d));
    return {
      hoy: hoyTexto,
      periodo_actual: per,
      sedes: d.sedes.map(sedeDTO),
      categorias: d.categorias.map(categoriaDTO),
      estudiantes: d.estudiantes.map((e) => estudianteDTO(e, d)),
      sesiones_hoy: sesionesHoy,
      resumen: resumenConDatos(d, per)
    };
  }

  async function listarSesiones(fecha, limite) {
    const d = await cargarTodo();
    let lista = d.sesiones.slice();
    if (fecha) {
      validarFecha(fecha);
      lista = lista.filter((s) => s.fecha === fecha);
    }
    lista.sort((a, b) => b.fecha.localeCompare(a.fecha) || b.hora.localeCompare(a.hora));
    return lista.slice(0, Number(limite) || 30).map((s) => sesionDTO(s, d));
  }

  async function crearSesion(cuerpo) {
    const d = await cargarTodo();
    const sedeId = entero(cuerpo.sede_id, "sede_id");
    const categoriaId = entero(cuerpo.categoria_id, "categoria_id");
    const fecha = validarFecha(cuerpo.fecha);
    const hora = validarHora(cuerpo.hora);
    const entrenador = String(cuerpo.entrenador || "").trim();
    if (entrenador.length < 3) throw new Error("El nombre del entrenador debe tener al menos 3 caracteres.");
    if (!d.sedes.some((s) => s.id === sedeId)) throw new Error("La sede seleccionada no existe.");
    if (!d.categorias.some((c) => c.id === categoriaId)) throw new Error("La categoría seleccionada no existe.");

    let sesion = d.sesiones.find(
      (s) => s.sede_id === sedeId && s.categoria_id === categoriaId && s.fecha === fecha && s.hora === hora
    );
    if (!sesion) {
      sesion = {
        id: siguienteId(d.sesiones), sede_id: sedeId, categoria_id: categoriaId,
        fecha: fecha, hora: hora, entrenador: entrenador, creada_en: ahora()
      };
      d.sesiones.push(sesion);
      await put("sesiones", sesion);
    }
    return sesionDTO(sesion, d);
  }

  async function detalleSesion(sesionId) {
    const d = await cargarTodo();
    const sesion = d.sesiones.find((s) => s.id === entero(sesionId, "sesion_id"));
    if (!sesion) throw new Error("La sesión no existe.");

    const estudiantesSesion = d.estudiantes.filter(
      (e) => e.estado === "ACTIVO" && e.sede_id === sesion.sede_id && e.categoria_id === sesion.categoria_id
    );
    const asistencias = d.asistencias
      .filter((a) => a.sesion_id === sesion.id)
      .sort((a, b) => a.registrada_en.localeCompare(b.registrada_en));
    const nombrePorId = mapa(d.estudiantes);
    const presentes = asistencias.map((a) => ({
      estudiante_id: a.estudiante_id,
      estudiante: (nombrePorId.get(a.estudiante_id) || {}).nombre || "",
      metodo: a.metodo,
      registrada_en: a.registrada_en
    }));
    const idsPresentes = new Set(asistencias.map((a) => a.estudiante_id));
    const ausentes = estudiantesSesion
      .filter((e) => !idsPresentes.has(e.id))
      .sort((a, b) => a.nombre.localeCompare(b.nombre))
      .map((e) => ({ estudiante_id: e.id, estudiante: e.nombre }));
    const avisos = d.avisos
      .filter((a) => a.sesion_id === sesion.id)
      .sort((a, b) => a.estado.localeCompare(b.estado) || b.id - a.id)
      .map((a) => avisoDTO(a, d));

    return {
      sesion: sesionDTO(sesion, d),
      presentes: presentes,
      ausentes: ausentes,
      avisos: avisos,
      stats: {
        presentes: presentes.length,
        ausentes: ausentes.length,
        avisos_pendientes: avisos.filter((a) => a.estado === "PENDIENTE").length
      }
    };
  }

  async function registrarAsistencia(sesionId, cuerpo) {
    const d = await cargarTodo();
    const metodo = String(cuerpo.metodo || "QR").trim().toUpperCase();
    if (!["QR", "MANUAL"].includes(metodo)) throw new Error("El método debe ser 'QR' o 'MANUAL'.");

    const sesion = d.sesiones.find((s) => s.id === entero(sesionId, "sesion_id"));
    if (!sesion) throw new Error("La sesión no existe.");

    let estudiante = null;
    if (cuerpo.qr_token) {
      const token = String(cuerpo.qr_token).trim().toUpperCase();
      estudiante = d.estudiantes.find((e) => e.qr_token.toUpperCase() === token);
    } else if (cuerpo.estudiante_id !== undefined && cuerpo.estudiante_id !== null && cuerpo.estudiante_id !== "") {
      estudiante = d.estudiantes.find((e) => e.id === entero(cuerpo.estudiante_id, "estudiante_id"));
    } else {
      throw new Error("Debe indicar un código QR o un estudiante.");
    }

    if (!estudiante) throw new Error("No se encontró un estudiante con ese código QR o ID.");
    if (estudiante.estado !== "ACTIVO") throw new Error("El estudiante está inactivo y no puede registrar asistencia.");
    if (estudiante.sede_id !== sesion.sede_id || estudiante.categoria_id !== sesion.categoria_id) {
      throw new Error("El estudiante no pertenece a la sede y categoría de esta sesión.");
    }
    if (d.asistencias.some((a) => a.sesion_id === sesion.id && a.estudiante_id === estudiante.id)) {
      throw new Error(`${estudiante.nombre} ya está registrado en esta sesión.`);
    }

    const asistencia = {
      id: siguienteId(d.asistencias),
      sesion_id: sesion.id,
      estudiante_id: estudiante.id,
      metodo: metodo,
      registrada_en: ahora()
    };
    await put("asistencias", asistencia);
    return {
      id: asistencia.id,
      estudiante_id: estudiante.id,
      estudiante: estudiante.nombre,
      metodo: metodo,
      mensaje: "Asistencia registrada"
    };
  }

  async function generarAvisos(sesionId) {
    const d = await cargarTodo();
    const sesion = d.sesiones.find((s) => s.id === entero(sesionId, "sesion_id"));
    if (!sesion) throw new Error("La sesión no existe.");

    const idsPresentes = new Set(
      d.asistencias.filter((a) => a.sesion_id === sesion.id).map((a) => a.estudiante_id)
    );
    const ausentes = d.estudiantes.filter(
      (e) => e.estado === "ACTIVO" && e.sede_id === sesion.sede_id &&
             e.categoria_id === sesion.categoria_id && !idsPresentes.has(e.id)
    );

    let creados = 0;
    for (const estudiante of ausentes) {
      const existe = d.avisos.some(
        (a) => a.sesion_id === sesion.id && a.estudiante_id === estudiante.id
      );
      if (!existe) {
        const aviso = {
          id: siguienteId(d.avisos),
          sesion_id: sesion.id,
          estudiante_id: estudiante.id,
          estado: "PENDIENTE",
          creada_en: ahora(),
          enviada_en: null
        };
        d.avisos.push(aviso);
        await put("avisos", aviso);
        creados += 1;
      }
    }
    return {
      ausentes: ausentes.length,
      creados: creados,
      ya_existian: ausentes.length - creados,
      pendientes: d.avisos.filter((a) => a.estado === "PENDIENTE").length
    };
  }

  async function listarAvisos(estado) {
    const d = await cargarTodo();
    let avisos = d.avisos.slice();
    if (estado) avisos = avisos.filter((a) => a.estado === String(estado).toUpperCase());
    avisos.sort((a, b) => a.estado.localeCompare(b.estado) || b.id - a.id);
    return avisos.map((a) => avisoDTO(a, d));
  }

  async function marcarAvisoEnviado(avisoId) {
    const d = await cargarTodo();
    const aviso = d.avisos.find((a) => a.id === entero(avisoId, "aviso_id"));
    if (!aviso || aviso.estado !== "PENDIENTE") {
      throw new Error("El aviso no existe o ya fue marcado como enviado.");
    }
    aviso.estado = "ENVIADA";
    aviso.enviada_en = ahora();
    await put("avisos", aviso);
    return avisoDTO(aviso, d);
  }

  async function listarCobros(periodo) {
    const d = await cargarTodo();
    return listarCobrosConDatos(d, validarPeriodo(periodo));
  }

  async function marcarPago(cuerpo) {
    const d = await cargarTodo();
    const periodo = validarPeriodo(cuerpo.periodo);
    const estado = String(cuerpo.estado || "").trim().toUpperCase();
    if (!["PAGADO", "PENDIENTE"].includes(estado)) {
      throw new Error("El estado de pago debe ser 'PAGADO' o 'PENDIENTE'.");
    }
    const estudiante = d.estudiantes.find((e) => e.id === entero(cuerpo.estudiante_id, "estudiante_id"));
    if (!estudiante) throw new Error("El estudiante no existe.");

    const cobro = cobroDTO(d, estudiante, periodo);
    if (cobro.monto <= 0) {
      throw new Error(
        `No hay monto a cobrar para este estudiante en el periodo (${cobro.motivo.replace(/_/g, " ").toLowerCase()}).`
      );
    }

    let pago = d.pagos.find((p) => p.estudiante_id === estudiante.id && p.periodo === periodo);
    if (!pago) {
      pago = { id: siguienteId(d.pagos), estudiante_id: estudiante.id, periodo: periodo };
      d.pagos.push(pago);
    }
    pago.monto = cobro.monto;
    pago.estado = estado;
    pago.fecha_pago = estado === "PAGADO" ? ahora() : null;
    await put("pagos", pago);
    return cobroDTO(d, estudiante, periodo);
  }

  async function resumen(periodo) {
    const d = await cargarTodo();
    return resumenConDatos(d, validarPeriodo(periodo || periodoActual()));
  }

  // -------------------------------------------------------------------
  // Despachador: mismo contrato HTTP que /api/escuela
  // -------------------------------------------------------------------

  function soporta(ruta) {
    return String(ruta || "").indexOf("/api/escuela/") === 0;
  }

  async function llamar(ruta, opciones) {
    await sembrarSiNecesario();
    const url = new URL(String(ruta), (global.location && global.location.origin) || "http://localhost");
    const rutaPath = url.pathname;
    const metodo = String((opciones && opciones.method) || "GET").toUpperCase();
    let cuerpo = {};
    if (opciones && opciones.body) {
      try {
        cuerpo = typeof opciones.body === "string" ? JSON.parse(opciones.body) : opciones.body;
      } catch (err) {
        cuerpo = {};
      }
    }

    let coincidencia;
    if (rutaPath === "/api/escuela/contexto" && metodo === "GET") {
      return clon(await contexto(url.searchParams.get("periodo")));
    }
    if (rutaPath === "/api/escuela/sesiones" && metodo === "GET") {
      return clon({ sesiones: await listarSesiones(url.searchParams.get("fecha")) });
    }
    if (rutaPath === "/api/escuela/sesiones" && metodo === "POST") {
      return clon({ sesion: await crearSesion(cuerpo), mensaje: "Sesión abierta" });
    }
    if ((coincidencia = rutaPath.match(/^\/api\/escuela\/sesiones\/(\d+)\/asistencia$/)) && metodo === "POST") {
      return clon(await registrarAsistencia(coincidencia[1], cuerpo));
    }
    if ((coincidencia = rutaPath.match(/^\/api\/escuela\/sesiones\/(\d+)\/avisos$/)) && metodo === "POST") {
      return clon(await generarAvisos(coincidencia[1]));
    }
    if ((coincidencia = rutaPath.match(/^\/api\/escuela\/sesiones\/(\d+)$/)) && metodo === "GET") {
      return clon(await detalleSesion(coincidencia[1]));
    }
    if (rutaPath === "/api/escuela/avisos" && metodo === "GET") {
      return clon({ avisos: await listarAvisos(url.searchParams.get("estado")) });
    }
    if ((coincidencia = rutaPath.match(/^\/api\/escuela\/avisos\/(\d+)\/enviado$/)) && metodo === "POST") {
      return clon(await marcarAvisoEnviado(coincidencia[1]));
    }
    if (rutaPath === "/api/escuela/cobros" && metodo === "GET") {
      return clon(await listarCobros(url.searchParams.get("periodo")));
    }
    if (rutaPath === "/api/escuela/cobros" && metodo === "POST") {
      const cobro = await marcarPago(cuerpo);
      return clon({ cobro: cobro, mensaje: "Estado de pago actualizado" });
    }
    if (rutaPath === "/api/escuela/resumen" && metodo === "GET") {
      return clon(await resumen(url.searchParams.get("periodo")));
    }
    throw new Error("Ruta no soportada en modo local: " + rutaPath);
  }

  function qrDataURL(token) {
    if (!global.qrcode) throw new Error("La librería QR no está cargada.");
    const qr = global.qrcode(0, "M");
    qr.addData(String(token || "").trim());
    qr.make();
    return qr.createDataURL(6, 2);
  }

  function reiniciarDemo() {
    promesaDB = null;
    promesaSiembra = null;
    return new Promise((resolve, reject) => {
      const peticion = indexedDB.deleteDatabase(DB_NAME);
      peticion.onsuccess = () => resolve();
      peticion.onerror = () => reject(peticion.error || new Error("No se pudo borrar la base local."));
      peticion.onblocked = () => resolve();
    });
  }

  global.API_LOCAL = {
    soporta: soporta,
    llamar: llamar,
    qrDataURL: qrDataURL,
    reiniciarDemo: reiniciarDemo
  };
})(window);
