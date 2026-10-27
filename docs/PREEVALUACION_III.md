# Preparación de la preevaluación III

El proyecto del Escritorio incorpora los seis mantenedores con vistas de clase y formularios de Django. Crear y editar usan el mismo modal Bootstrap; eliminar pide confirmación con SweetAlert2 y envía un POST protegido por CSRF. Los recursos de estas pantallas se incluyen localmente: Bootstrap 5.3.8 y SweetAlert2 11.26.3 con sus licencias.

## Iniciar y entrar

```bash
cd ~/Desktop/sgr-municipalidad-laserena
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

Si aún no existe una cuenta, ejecutar `python manage.py createsuperuser` antes de iniciar el servidor. El inicio no precarga registros. Por solicitud del usuario se recuperaron los datos de `database/sgr_laserena.db` con `python manage.py recuperar_datos_anteriores`: 7 delegaciones, 5 roles, 9 usuarios, 5 ítems y metas, 5 tipos, 10 subatenciones y 3 atenciones. La importación es atómica, no duplica registros al repetirse y conserva la contraseña de la cuenta actual. La base anterior permanece intacta y el `.env` existente se conserva.

Entrar a `http://127.0.0.1:8000/` y seleccionar un mantenedor del menú. También se puede abrir `http://127.0.0.1:8000/gestion/delegaciones/`: si falta sesión, Django redirige a `/acceso/` y vuelve al listado después de validar usuario, correo o RUT y contraseña.

## Rutas de los mantenedores

| Entidad | Listado | Formulario | Clases en gestion/crud_views.py |
| --- | --- | --- | --- |
| Delegaciones | /gestion/delegaciones/ | DelegacionForm | DelegacionListView, DelegacionCreateView, DelegacionUpdateView, DelegacionDeleteView |
| Roles | /gestion/roles/ | RolForm | RolListView, RolCreateView, RolUpdateView, RolDeleteView |
| Usuarios | /gestion/usuarios/ | UsuarioForm | UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView |
| Ítems y metas | /gestion/items-metas/ | ItemMetaForm | ItemMetaListView, ItemMetaCreateView, ItemMetaUpdateView, ItemMetaDeleteView |
| Tipos de atención | /gestion/tipos-atencion/ | TipoAtencionForm | TipoAtencionListView, TipoAtencionCreateView, TipoAtencionUpdateView, TipoAtencionDeleteView |
| Subatenciones | /gestion/sub-atenciones/ | SubAtencionForm | SubAtencionListView, SubAtencionCreateView, SubAtencionUpdateView, SubAtencionDeleteView |

Para cada listado: `nuevo/` crea, `<id>/editar/` edita y `<id>/eliminar/` confirma/elimina. El GET de eliminación no borra datos; solo el POST puede hacerlo. Se conserva el borrado físico con relaciones protegidas de los modelos existentes.

## Recorrido para la defensa individual

1. Iniciar el servidor y entrar con una cuenta propia. Explicar el modelo `Usuario`, la sesión y el acceso en `AccesoView` y `AccesoForm`.
2. Elegir un mantenedor por integrante. Mostrar listado, crear un registro propio, recargar y explicar cómo persiste en la base.
3. Enviar un formulario inválido y observar el mismo modal abierto con errores del servidor. Corregir y guardar.
4. Editar el registro. Explicar que `UpdateView` carga una instancia y reutiliza el mismo `ModelForm` que `CreateView`.
5. Cancelar una eliminación y comprobar que el registro permanece. Volver a eliminar, confirmar SweetAlert2 y explicar el POST con `{% csrf_token %}` y la `DeleteView`.
6. Buscar por nombre/código (usuarios también por correo/RUT), filtrar por estado, elegir orden ascendente o descendente y recorrer páginas. Mostrar `q`, `estado`, `order`, `page_size` y `page` en la URL y cómo se conservan después de guardar. Usuarios y subatenciones tienen filtro adicional por delegación/tipo. Elegir 5, 15 o 30 registros, recargar y comprobar que el tamaño se conserva en sesión por mantenedor.
7. Con un usuario de lectura, intentar la URL directa de crear, editar o eliminar. El servidor devuelve 403 aunque se escriba manualmente la URL. Un usuario sin sesión es enviado al login.

Para demostrar paginación con cinco filas hacen falta al menos seis registros que cumplan los filtros. Prepararlos como datos de la demostración; la instalación no los crea automáticamente. El tamaño inicial es 15. Limpiar filtros conserva la preferencia de tamaño en sesión y vuelve al orden por nombre.

## Mapa de los criterios y código

| Criterio de la pauta | Implementación | Dónde explicarlo |
| --- | --- | --- |
| Ejecución local y login (5 pts) | Django, autenticación, sesión, retorno a `next` | `manage.py`, `sgr/settings.py`, `sgr/urls.py`, `gestion/forms.py:AccesoForm`, `gestion/crud_views.py:AccesoView` |
| CRUD completo (15 pts) | Clases específicas, ModelForm y ORM | `gestion/models.py`, `gestion/forms.py`, `gestion/crud_views.py`, `gestion/urls.py` |
| Bootstrap + SweetAlert2 (8 pts) | Modal compartido; confirmación y POST de eliminación | `gestion/templates/gestion/_form_modal.html`, `list.html`, `confirm_delete.html`, `gestion/static/gestion/crud.js` |
| Buscador, filtro y paginación (12 pts) | Consulta `Q`, filtros y `Paginator` con parámetros conservados; tamaños 5/15/30 y orden permitido | `CrudAccessMixin.filtered_queryset`, `get_page_size`, `get_ordering`, `query_parameters`, `get_context_data`, `{% querystring query_params %}` en `list.html` |

El puntaje depende también de que cada integrante explique el código y demuestre los flujos. La implementación y las pruebas no reemplazan esa defensa individual.

## Qué hace cada componente

- `ModelForm.Meta.fields` limita los campos que puede enviar el usuario. `clean_nombre`, `clean_rut`, `clean_email` y `clean` validan antes de guardar. El código automático se genera en la vista dentro de una transacción. Las restricciones únicas y las claves foráneas siguen en la base de datos.
- `LoginRequiredMixin` exige sesión. `PermissionRequiredMixin` comprueba `view`, `add`, `change` o `delete` del modelo. `CrudAccessMixin` exige también una cuenta activa y un alcance territorial válido para consultar usuarios.
- `gestion/permissions.py` traduce los roles SGR a Groups nativos. `signals.py` sincroniza al guardar usuarios/roles y después de `migrate`. Si se cargaron usuarios por otro mecanismo, se puede ejecutar `python manage.py sincronizar_roles`. Los permisos directos y los grupos externos se conservan.
- `get_success_url` vuelve al listado conservando los parámetros permitidos. Una página fuera de rango se ajusta con `Paginator.get_page`, por ejemplo tras eliminar el último elemento de una página.
- `get_page_size` valida únicamente 5, 15 o 30 y recuerda la elección por catálogo en `request.session`. Un tamaño inválido conserva la última preferencia válida. `get_ordering` permite únicamente las opciones visibles; `id` desempata valores iguales para mantener páginas estables. Los parámetros adicionales del navegador no se convierten en campos arbitrarios del ORM.
- `filtered_queryset` aplica primero el alcance, luego búsqueda y filtros, después ordenamiento. `get_context_data` pagina ese resultado. El formulario GET reinicia la página al aplicar una nueva consulta; los enlaces y el retorno de crear/editar/eliminar conservan la consulta validada.
- `open_modal=True` abre Bootstrap después de cargar la página, tanto en GET como tras POST inválido. Un POST válido guarda y redirige: patrón POST/Redirect/GET. No se usa AJAX para estas operaciones.
- SweetAlert2 pregunta; Django elimina. Los nombres llegan como texto escapado en atributos, no se concatenan dentro de código JavaScript. Un registro referenciado se conserva y devuelve un mensaje comprensible.

## Permisos y datos de usuarios

`ROL01` tiene todos los mantenedores; `ROL02` gestiona catálogos de coordinación; `ROL03` gestiona usuarios territoriales y metas; `ROL04` conserva atención ciudadana; `ROL05` dispone de lectura de los catálogos habilitados. Un rol con `permisos=total` administra todos los mantenedores. Los superusuarios tienen los permisos nativos completos.

Los delegados solo pueden administrar operadores/consultores de su propia delegación que no tengan permisos totales. El ModelForm limita las opciones y la vista limita el queryset, incluso en una URL directa. La API de compatibilidad aplica la misma restricción. Un delegado sin delegación no accede a la gestión de usuarios. La contraseña de una cuenta nueva se define explícitamente y se guarda con `set_password`; al editar, dejarla vacía mantiene la clave anterior. Las fotos existentes se conservan y el perfil sigue permitiendo actualizarlas.

## Verificación

```bash
python manage.py test gestion
python manage.py check
python manage.py makemigrations --check --dry-run
```

La API `/api/` sigue disponible para atenciones, perfil y compatibilidad. Los botones de los seis mantenedores llevan ahora a las páginas Django. Los modales anteriores de la interfaz histórica no son el flujo usado para defender estos CRUD.

## Límites de esta etapa

El trabajo cubre los seis CRUD de la preevaluación y sus consultas protegidas. No modifica el esquema de los modelos ni introduce borrado lógico o un `BaseModel` de auditoría. La eliminación sigue siendo física, con relaciones `PROTECT`; esos cambios estructurales requieren otra migración y una política de historial. Atenciones mantiene sus reglas originales y no se presenta como CRUD completo.

## Verificación realizada el 27 de octubre de 2026

- 58 pruebas Django y 23 pruebas JavaScript de los flujos vigentes aprobadas.
- check sin incidencias; makemigrations --check --dry-run sin cambios; recursos estáticos preparados.
- En navegador, con base temporal: login, creación y edición con persistencia, errores del servidor dentro del modal Bootstrap, confirmación SweetAlert2 y cancelación, búsqueda/filtro/orden/página combinados y preferencia de tamaño.
- El borrado por POST, las relaciones protegidas y el acceso por URL directa se verificaron también en las pruebas Django.
- Se corrigió y cubrió con pruebas el caso de un delegado que intentaba asignar o editar un rol con permisos totales, tanto en formularios como en API.
- La aplicación se ejecuta desde la carpeta del Escritorio en http://127.0.0.1:8000/. El entorno de demostración usa otra base y no agrega registros ficticios a la base habitual.
- Cambios locales conservados en la rama existente, sin publicar en GitHub.

## Identidad visual original conservada

Las páginas Django heredan de index.html y reutilizan la misma cabecera, logo horizontal, barra lateral con sus iconos, selector de delegación, perfil personal y pie municipal. No existe una segunda barra de navegación alternativa. Los estilos de CRUD se limitan al contenido.

/acceso/ muestra el login original, con Mostrar contraseña y el flujo de recuperación existente. El formulario admite el POST de Django con CSRF y el acceso original con JavaScript conserva un destino next del mismo sitio. Desde un mantenedor se puede volver a Atención Ciudadana y a los módulos originales; el elemento activo del menú refleja la pantalla actual.

Los iconos Lucide se sirven también desde el proyecto para conservarlos sin depender de una descarga durante la demostración. La lógica de sesión, los ModelForm y las vistas de clase se mantienen.

Comprobación de identidad original: login y retorno al CRUD, perfil, navegación entre mantenedores y Atención Ciudadana, iconos, modal con errores y paginación verificados en navegador. La captura Interfaz_original_con_CRUD.png utiliza únicamente datos de la base temporal.


## RUT y código de rol

El RUT se valida por sintaxis y dígito verificador mediante módulo 11. Usuarios e Ingreso de Atención muestran el resultado en el navegador; el servidor vuelve a validar antes de guardar, normaliza el formato y rechaza RUT duplicados en usuarios. No consulta registros de identidad externos.

Al crear un rol desde `/gestion/roles/nuevo/` o `/api/roles`, el servidor genera su código con la secuencia `ROL` y evita códigos existentes. El formulario ya no solicita un código manual. Al editar, el código se conserva aunque se envíe otro valor.


La ejecución completa de `node --test tests/*.cjs` informa 25 pruebas aprobadas y 29 fallos heredados de `tests/test_ui_flows.cjs`, que todavía depende del modo local del prototipo. Los mismos 29 casos fallan en el commit base `e6b5972`; no aparecieron fallos adicionales. El caso de visibilidad inicial de la aplicación se verifica ahora sobre las respuestas HTML renderizadas de Django.
