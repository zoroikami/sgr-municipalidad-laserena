# CRUD Django para preevaluación III

Alcance: seis mantenedores existentes, sin importar datos ni modificar registros de negocio. Conservar atención, perfil y API de compatibilidad. Trabajo local, sin push o despliegue.
Arquitectura: CBV explícitas por entidad, ModelForm reutilizado por Create/Update, templates de Django, Bootstrap 5 Modal y SweetAlert2 para Delete por POST+CSRF. Consulta ORM con q, estado, delegacion/tipo cuando corresponda y paginación que conserva parámetros. LoginRequiredMixin y PermissionRequiredMixin, Groups sincronizados con roles existentes y usuarios territoriales limitados por delegación.
Verificación: suite Django actual primero (19 pruebas aprobadas), nuevas pruebas de CRUD, permisos, formularios y combinación de parámetros; navegador con BD temporal aislada. Bootstrap/SweetAlert locales para demostración sin CDN.

- [x] Escribir pruebas funcionales y comprobar fallo por rutas ausentes.
- [x] Formularios, CBV, permisos y rutas bajo /gestion/.
- [x] Templates de listado, modal compartido, login y confirmación; recursos estáticos locales.
- [x] Enlazar mantenedores desde interfaz actual; preservar API y perfil.
- [x] Verificar pruebas, navegación real y documentación para defensa individual.

Criterios verificables: cada mantenedor lista, crea, edita y elimina o informa relación protegida; modal se reabre con errores; Delete nunca elimina por GET; acceso anónimo redirige a login y usuario sin permiso recibe 403; filtros persisten al paginar y guardar. La defensa oral corresponde al estudiante; no se garantiza puntaje por funcionamiento automático.
