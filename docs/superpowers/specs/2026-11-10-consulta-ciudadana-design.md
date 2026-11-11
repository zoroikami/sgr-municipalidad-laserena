# Consulta ciudadana sin cuenta

El usuario aprobó una página anterior al login, con la estética municipal existente, y consulta mediante folio y código privado enviado por correo.

- La raíz muestra Consultar mi atención a visitantes sin sesión y mantiene el dashboard para usuarios autenticados. El login de funcionarios conserva su URL y ofrece volver a la consulta ciudadana.
- El formulario público recibe folio y código exclusivamente por POST. Muestra solo folio, estado, fechas y delegación, sin nombres, RUT, correos, descripciones ni acceso al CRUD.
- Atencion incorpora correo del solicitante, hash del código y fecha de envío. El correo es opcional para conservar registros existentes y atenciones presenciales. Al registrar o cambiar un correo se envía un código; una acción autorizada permite reenviar/renovar el acceso. Sin correo no se habilita la consulta pública.
- Los códigos tienen 100 bits aleatorios, formato legible y 30 días de vigencia. Solo se conserva un HMAC, ligado a la atención. Renovar o cambiar el correo invalida el código anterior; el correo nunca contiene información privada de la atención.
- SMTP se ejecuta después de confirmar el guardado de la atención. Un fallo conserva el registro y se informa sin afirmar que se envió el correo; un reenvío fallido conserva el código anterior válido. El código no se muestra a funcionarios ni se registra en logs.
- La consulta aplica un límite compartido de 30 intentos por IP cada 15 minutos con Redis. Los códigos incorrectos, vencidos, archivados o desconocidos producen la misma respuesta. Si Redis falla, la consulta se detiene con un mensaje temporal. Se confía en X-Real-IP únicamente detrás del proxy Nginx ya configurado.
- Respuestas privadas sin caché y sin referente a otros sitios; CSRF obligatorio. No hay recuperación pública por RUT ni consulta por ID, ni envíos anónimos de correo.
- La interfaz conserva logo, paleta, fuente y tokens municipales. El resultado presenta el estado como elemento principal y el acceso de funcionarios como acción secundaria. Se verifica teclado y diseño en escritorio y teléfono.

Validación: pruebas de propiedad, aislamiento de permisos existentes, envío/cambio/reenvío/caducidad, fallos SMTP/Redis y POST inválidos. Recorrido real con Mailpit: registrar con correo, abrir email, consultar sin sesión y rechazar el código de otra atención. Después, commit/push y despliegue AWS según la autorización vigente; las pruebas no envían correo a terceros en producción.
