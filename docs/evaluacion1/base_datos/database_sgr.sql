-- =============================================================================
-- SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - ILUSTRE MUNICIPALIDAD DE LA SERENA
-- SCRIPT DE BASE DE DATOS RELACIONAL PARA MYSQL 8.0 / MARIADB 10.5+
-- ASIGNATURA: Proyecto Integrado | PROFESOR: Jorge Cortés | INSTITUCIÓN: INACAP
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `sgr_laserena_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `sgr_laserena_db`;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `registro_auditoria`, `indicador_desempeno`, `historial_compromiso`, 
    `compromiso_agenda`, `atencion_social`, `persona_usuaria`, `validacion_evidencia`, 
    `evidencia`, `actividad`, `meta_item`, `item_medicion`, `periodo_medicion`, 
    `usuario_rol`, `usuario`, `cargo`, `rol`, `delegacion`;
SET FOREIGN_KEY_CHECKS = 1;

-- Delegaciones
CREATE TABLE `delegacion` (
    `id_delegacion` INT AUTO_INCREMENT PRIMARY KEY,
    `codigo` VARCHAR(20) NOT NULL UNIQUE,
    `nombre` VARCHAR(100) NOT NULL,
    `direccion` VARCHAR(200) NOT NULL,
    `telefono` VARCHAR(25) NOT NULL,
    `activa` BOOLEAN NOT NULL DEFAULT 1,
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Roles
CREATE TABLE `rol` (
    `id_rol` INT AUTO_INCREMENT PRIMARY KEY,
    `codigo` VARCHAR(30) NOT NULL UNIQUE,
    `nombre` VARCHAR(80) NOT NULL,
    `descripcion` VARCHAR(255) NULL
) ENGINE=InnoDB;

-- Cargos
CREATE TABLE `cargo` (
    `id_cargo` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre_cargo` VARCHAR(100) NOT NULL UNIQUE,
    `departamento` VARCHAR(100) NOT NULL,
    `activo` BOOLEAN NOT NULL DEFAULT 1
) ENGINE=InnoDB;

-- Usuarios
CREATE TABLE `usuario` (
    `id_usuario` INT AUTO_INCREMENT PRIMARY KEY,
    `id_delegacion` INT NOT NULL,
    `id_cargo` INT NOT NULL,
    `rut` VARCHAR(12) NOT NULL UNIQUE,
    `nombres` VARCHAR(100) NOT NULL,
    `apellidos` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `estado` ENUM('Activo', 'Inactivo', 'Suspendido') NOT NULL DEFAULT 'Activo',
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_usuario_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_usuario_cargo` FOREIGN KEY (`id_cargo`) 
        REFERENCES `cargo` (`id_cargo`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Usuario_Rol N:M
CREATE TABLE `usuario_rol` (
    `id_usuario` INT NOT NULL,
    `id_rol` INT NOT NULL,
    `asignado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_usuario`, `id_rol`),
    CONSTRAINT `fk_usuariorol_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_usuariorol_rol` FOREIGN KEY (`id_rol`) 
        REFERENCES `rol` (`id_rol`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Período de Medición
CREATE TABLE `periodo_medicion` (
    `id_periodo` INT AUTO_INCREMENT PRIMARY KEY,
    `codigo` VARCHAR(20) NOT NULL UNIQUE,
    `nombre` VARCHAR(100) NOT NULL,
    `fecha_inicio` DATE NOT NULL,
    `fecha_termino` DATE NOT NULL,
    `dias_totales` INT NOT NULL,
    `activo` BOOLEAN NOT NULL DEFAULT 0,
    CONSTRAINT `chk_fechas_periodo` CHECK (`fecha_termino` > `fecha_inicio`)
) ENGINE=InnoDB;

-- Ítems Medibles
CREATE TABLE `item_medicion` (
    `id_item` INT AUTO_INCREMENT PRIMARY KEY,
    `codigo` VARCHAR(30) NOT NULL UNIQUE,
    `nombre_item` VARCHAR(150) NOT NULL,
    `unidad_medida` VARCHAR(50) NOT NULL,
    `descripcion` TEXT NULL,
    `activo` BOOLEAN NOT NULL DEFAULT 1
) ENGINE=InnoDB;

-- Metas y Ponderadores
CREATE TABLE `meta_item` (
    `id_meta` INT AUTO_INCREMENT PRIMARY KEY,
    `id_periodo` INT NOT NULL,
    `id_cargo` INT NOT NULL,
    `id_item` INT NOT NULL,
    `meta_cantidad` INT NOT NULL,
    `ponderacion_porcentaje` DECIMAL(5,2) NOT NULL,
    CONSTRAINT `chk_ponderacion_rango` CHECK (`ponderacion_porcentaje` > 0 AND `ponderacion_porcentaje` <= 100),
    CONSTRAINT `uq_meta_periodo_cargo_item` UNIQUE (`id_periodo`, `id_cargo`, `id_item`),
    CONSTRAINT `fk_meta_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo_medicion` (`id_periodo`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_meta_cargo` FOREIGN KEY (`id_cargo`) 
        REFERENCES `cargo` (`id_cargo`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_meta_item` FOREIGN KEY (`id_item`) 
        REFERENCES `item_medicion` (`id_item`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Actividades
CREATE TABLE `actividad` (
    `id_actividad` INT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NOT NULL,
    `id_delegacion` INT NOT NULL,
    `id_item` INT NOT NULL,
    `codigo_actividad` VARCHAR(30) NOT NULL UNIQUE,
    `fecha_realizacion` DATE NOT NULL,
    `sector_territorio` VARCHAR(150) NOT NULL,
    `solicitante` VARCHAR(150) NOT NULL,
    `telefono_contacto` VARCHAR(25) NULL,
    `descripcion` TEXT NOT NULL,
    `estado_registro` ENUM('Registrada', 'Anulada') NOT NULL DEFAULT 'Registrada',
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_actividad_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_actividad_item` FOREIGN KEY (`id_item`) 
        REFERENCES `item_medicion` (`id_item`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Evidencias (1:1 con actividad)
CREATE TABLE `evidencia` (
    `id_evidencia` INT AUTO_INCREMENT PRIMARY KEY,
    `id_actividad` INT NOT NULL UNIQUE,
    `codigo_evidencia` VARCHAR(30) NOT NULL UNIQUE,
    `ruta_fotografia` VARCHAR(255) NOT NULL,
    `georreferencia` VARCHAR(100) NULL,
    `estado_validacion` ENUM('Pendiente', 'Aprobada', 'Rechazada', 'En_Correccion') NOT NULL DEFAULT 'Pendiente',
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_evidencia_actividad` FOREIGN KEY (`id_actividad`) 
        REFERENCES `actividad` (`id_actividad`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Validaciones
CREATE TABLE `validacion_evidencia` (
    `id_validacion` INT AUTO_INCREMENT PRIMARY KEY,
    `id_evidencia` INT NOT NULL,
    `id_verificador` INT NOT NULL,
    `fecha_validacion` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `dictamen` ENUM('Aprobado', 'Rechazado', 'Requiere_Correccion') NOT NULL,
    `observacion_tecnica` TEXT NULL,
    CONSTRAINT `fk_validacion_evidencia` FOREIGN KEY (`id_evidencia`) 
        REFERENCES `evidencia` (`id_evidencia`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_validacion_verificador` FOREIGN KEY (`id_verificador`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Personas Usuarias (Social)
CREATE TABLE `persona_usuaria` (
    `id_persona` INT AUTO_INCREMENT PRIMARY KEY,
    `rut` VARCHAR(12) NOT NULL UNIQUE,
    `nombre_completo` VARCHAR(150) NOT NULL,
    `direccion` VARCHAR(200) NOT NULL,
    `telefono` VARCHAR(25) NULL,
    `id_delegacion` INT NOT NULL,
    `total_gestiones_periodo` INT NOT NULL DEFAULT 1,
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `chk_tope_gestiones` CHECK (`total_gestiones_periodo` >= 1 AND `total_gestiones_periodo` <= 3),
    CONSTRAINT `fk_persona_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Atenciones Sociales Multietapa
CREATE TABLE `atencion_social` (
    `id_atencion` INT AUTO_INCREMENT PRIMARY KEY,
    `id_persona` INT NOT NULL,
    `id_gestor` INT NOT NULL,
    `numero_gestion` INT NOT NULL,
    `fecha_atencion` DATE NOT NULL,
    `tipo_beneficio` VARCHAR(100) NOT NULL,
    `detalle_intervencion` TEXT NOT NULL,
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `chk_numero_gestion` CHECK (`numero_gestion` >= 1 AND `numero_gestion` <= 3),
    CONSTRAINT `uq_persona_gestion` UNIQUE (`id_persona`, `numero_gestion`),
    CONSTRAINT `fk_atencion_persona` FOREIGN KEY (`id_persona`) 
        REFERENCES `persona_usuaria` (`id_persona`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_atencion_gestor` FOREIGN KEY (`id_gestor`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Compromisos de Agenda Colectiva
CREATE TABLE `compromiso_agenda` (
    `id_compromiso` INT AUTO_INCREMENT PRIMARY KEY,
    `id_delegacion` INT NOT NULL,
    `id_responsable` INT NOT NULL,
    `codigo_compromiso` VARCHAR(30) NOT NULL UNIQUE,
    `origen_solicitud` VARCHAR(150) NOT NULL,
    `solicitante_dirigente` VARCHAR(150) NOT NULL,
    `sector_territorio` VARCHAR(150) NOT NULL,
    `direccion_municipal` VARCHAR(100) NOT NULL,
    `fecha_ingreso` DATE NOT NULL,
    `fecha_limite` DATE NOT NULL,
    `estado` ENUM('Ingresado', 'Pendiente', 'En_Proceso', 'Realizado') NOT NULL DEFAULT 'Ingresado',
    `prioridad` ENUM('Baja', 'Media', 'Alta', 'Urgente') NOT NULL DEFAULT 'Media',
    `observaciones` TEXT NULL,
    `creado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_compromiso_delegacion` FOREIGN KEY (`id_delegacion`) 
        REFERENCES `delegacion` (`id_delegacion`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_compromiso_responsable` FOREIGN KEY (`id_responsable`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Historial Compromiso
CREATE TABLE `historial_compromiso` (
    `id_historial` INT AUTO_INCREMENT PRIMARY KEY,
    `id_compromiso` INT NOT NULL,
    `id_usuario_cambio` INT NOT NULL,
    `estado_anterior` ENUM('Ingresado', 'Pendiente', 'En_Proceso', 'Realizado') NOT NULL,
    `estado_nuevo` ENUM('Ingresado', 'Pendiente', 'En_Proceso', 'Realizado') NOT NULL,
    `fecha_cambio` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `motivo` VARCHAR(255) NULL,
    CONSTRAINT `fk_historial_compromiso` FOREIGN KEY (`id_compromiso`) 
        REFERENCES `compromiso_agenda` (`id_compromiso`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_historial_usuario` FOREIGN KEY (`id_usuario_cambio`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Indicador de Desempeño
CREATE TABLE `indicador_desempeno` (
    `id_indicador` INT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NOT NULL,
    `id_periodo` INT NOT NULL,
    `fecha_calculo` DATE NOT NULL,
    `porcentaje_ponderado` DECIMAL(5,2) NOT NULL,
    `semaforo` ENUM('Verde', 'Ambar', 'Rojo') NOT NULL,
    `dias_transcurridos` INT NOT NULL,
    `meta_esperada_dia` DECIMAL(5,2) NOT NULL,
    `calculado_en` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_indicador_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_indicador_periodo` FOREIGN KEY (`id_periodo`) 
        REFERENCES `periodo_medicion` (`id_periodo`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Registro de Auditoría
CREATE TABLE `registro_auditoria` (
    `id_auditoria` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `id_usuario` INT NULL,
    `fecha_hora` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `accion` VARCHAR(80) NOT NULL,
    `tabla_afectada` VARCHAR(60) NOT NULL,
    `id_registro_afectado` VARCHAR(50) NULL,
    `ip_origen` VARCHAR(45) NOT NULL,
    `datos_previos` JSON NULL,
    `datos_nuevos` JSON NULL,
    CONSTRAINT `fk_auditoria_usuario` FOREIGN KEY (`id_usuario`) 
        REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Índices de Rendimiento
CREATE INDEX `idx_actividad_fecha` ON `actividad` (`fecha_realizacion`);
CREATE INDEX `idx_evidencia_codigo` ON `evidencia` (`codigo_evidencia`);
CREATE INDEX `idx_compromiso_estado_fecha` ON `compromiso_agenda` (`estado`, `fecha_limite`);

-- =============================================================================
-- DATOS SEMILLA (SEED DATA)
-- =============================================================================
INSERT INTO `delegacion` (`id_delegacion`, `codigo`, `nombre`, `direccion`, `telefono`) VALUES
(1, 'DEL-CENTRO', 'Delegación Centro', 'Prat 451, La Serena', '+56 51 220 6600'),
(2, 'DEL-COMPANIAS', 'Delegación Las Compañías', 'Esmeralda 2451, Las Compañías', '+56 51 220 6700'),
(3, 'DEL-PAMPA', 'Delegación La Pampa', 'Juan de Dios Pení 150, La Pampa', '+56 51 220 6800'),
(4, 'DEL-ANTENA', 'Delegación La Antena - La Florida', '18 de Septiembre 420, La Antena', '+56 51 220 6900'),
(5, 'DEL-MAR', 'Delegación Avenida del Mar', 'Av. del Mar 2100, La Serena', '+56 51 220 6500'),
(6, 'DEL-RURAL', 'Delegación Rural', 'Ruta 41 Km 15, Algarrobito', '+56 51 220 6400');

INSERT INTO `rol` (`id_rol`, `codigo`, `nombre`, `descripcion`) VALUES
(1, 'ROL_ADMIN', 'Administrador Central TI', 'Control de configuración y auditoría'),
(2, 'ROL_DELEGADO', 'Delegado Municipal', 'Supervisión de delegación y agenda'),
(3, 'ROL_VERIFICADOR', 'Verificador Técnico', 'Validación técnica de evidencias'),
(4, 'ROL_FUNCIONARIO', 'Funcionario Territorial', 'Captura de actividades en terreno'),
(5, 'ROL_GESTOR_SOCIAL', 'Gestor Social', 'Atención de casos sociales multietapa');

INSERT INTO `cargo` (`id_cargo`, `nombre_cargo`, `departamento`) VALUES
(1, 'Funcionario Territorial Terreno', 'Operaciones y Servicios Comunitarios'),
(2, 'Gestor Social de Delegación', 'Desarrollo Comunitario DISERCO'),
(3, 'Verificador Técnico de Calidad', 'Control de Gestión DISERCO'),
(4, 'Delegado Municipal Jurisdiccional', 'Gabinete Territorial'),
(5, 'Administrador Central SGR', 'Tecnologías de Información');

INSERT INTO `usuario` (`id_usuario`, `id_delegacion`, `id_cargo`, `rut`, `nombres`, `apellidos`, `email`, `password_hash`, `estado`) VALUES
(1, 2, 1, '16.421.890-5', 'Marcelo', 'Gómez Pastén', 'marcelo.gomez@laserena.cl', '$2b$12$hash_seguro', 'Activo'),
(2, 2, 2, '17.892.341-2', 'Camila', 'Rojas Barraza', 'camila.rojas@laserena.cl', '$2b$12$hash_seguro', 'Activo'),
(3, 1, 3, '14.561.982-K', 'Rodrigo', 'Pérez Santander', 'rodrigo.perez@laserena.cl', '$2b$12$hash_seguro', 'Activo'),
(4, 2, 4, '12.345.678-9', 'Álvaro', 'Valdebenito Cruz', 'alvaro.valdebenito@laserena.cl', '$2b$12$hash_seguro', 'Activo'),
(5, 1, 5, '15.678.901-3', 'Administrador', 'SGR La Serena', 'admin.sgr@laserena.cl', '$2b$12$hash_seguro', 'Activo');

INSERT INTO `usuario_rol` (`id_usuario`, `id_rol`) VALUES
(1, 4), (2, 5), (3, 3), (4, 2), (5, 1);

INSERT INTO `periodo_medicion` (`id_periodo`, `codigo`, `nombre`, `fecha_inicio`, `fecha_termino`, `dias_totales`, `activo`) VALUES
(1, '2026-Q3', 'Tercer Trimestre Q3 2026', '2026-07-01', '2026-09-30', 91, 1);

INSERT INTO `item_medicion` (`id_item`, `codigo`, `nombre_item`, `unidad_medida`, `descripcion`) VALUES
(1, 'ITM-01', 'Operativos en Terreno y Aseo Comunitario', 'Operativo', 'Limpieza y retiro de escombros'),
(2, 'ITM-02', 'Fiscalización e Inspección Territorial', 'Inspección', 'Notificaciones por ordenanza'),
(3, 'ITM-03', 'Fichas de Asistencia Social Multietapa', 'Caso Social', 'Atención y subsidios vecinales'),
(4, 'ITM-04', 'Audiencias Comunitarias y Mediación', 'Audiencia', 'Reuniones con juntas de vecinos');

-- Metas ponderadas al 100% exacto
INSERT INTO `meta_item` (`id_meta`, `id_periodo`, `id_cargo`, `id_item`, `meta_cantidad`, `ponderacion_porcentaje`) VALUES
(1, 1, 1, 1, 15, 50.00),
(2, 1, 1, 2, 25, 30.00),
(3, 1, 1, 4, 10, 20.00),
(4, 1, 2, 3, 30, 80.00),
(5, 1, 2, 4, 10, 20.00);

INSERT INTO `actividad` (`id_actividad`, `id_usuario`, `id_delegacion`, `id_item`, `codigo_actividad`, `fecha_realizacion`, `sector_territorio`, `solicitante`, `telefono_contacto`, `descripcion`) VALUES
(1, 1, 2, 1, 'ACT-2026-0001', '2026-09-10', 'Las Compañías - Villa Los Héroes', 'JJ.VV Los Héroes', '+56 9 8456 1234', 'Operativo de despeje de escombros en plazoleta central'),
(2, 2, 2, 3, 'ACT-2026-0002', '2026-09-12', 'Las Compañías - Pasaje Las Lilas', 'Teresa Araya Godoy', '+56 9 9231 4455', 'Entrega de canasta básica y evaluación técnica de subsidio');

INSERT INTO `evidencia` (`id_evidencia`, `id_actividad`, `codigo_evidencia`, `ruta_fotografia`, `georreferencia`, `estado_validacion`) VALUES
(1, 1, 'EVI-2026-0740', 'assets/evidencia_terreno.jpg', '-29.8921, -71.2534', 'Aprobada'),
(2, 2, 'EVI-2026-0742', 'assets/evidencia_social.jpg', '-29.8990, -71.2610', 'Aprobada');

INSERT INTO `validacion_evidencia` (`id_validacion`, `id_evidencia`, `id_verificador`, `dictamen`, `observacion_tecnica`) VALUES
(1, 1, 3, 'Aprobado', 'Fotografía nítida; se constata el retiro de escombros.'),
(2, 2, 3, 'Aprobado', 'Ficha social completa con recepción conforme.');

INSERT INTO `persona_usuaria` (`id_persona`, `rut`, `nombre_completo`, `direccion`, `telefono`, `id_delegacion`, `total_gestiones_periodo`) VALUES
(1, '11.890.432-1', 'Teresa Araya Godoy', 'Pasaje Las Lilas 450, Las Compañías', '+56 9 9231 4455', 2, 2);

INSERT INTO `atencion_social` (`id_atencion`, `id_persona`, `id_gestor`, `numero_gestion`, `fecha_atencion`, `tipo_beneficio`, `detalle_intervencion`) VALUES
(1, 1, 2, 1, '2026-07-15', 'Subsidio Agua Potable', 'Etapa 1: Evaluación socioeconómica inicial.'),
(2, 1, 2, 2, '2026-09-12', 'Ayuda Paliativa', 'Etapa 2: Entrega de canasta familiar.');

INSERT INTO `compromiso_agenda` (`id_compromiso`, `id_delegacion`, `id_responsable`, `codigo_compromiso`, `origen_solicitud`, `solicitante_dirigente`, `sector_territorio`, `direccion_municipal`, `fecha_ingreso`, `fecha_limite`, `estado`, `prioridad`, `observaciones`) VALUES
(1, 2, 1, 'CMP-2026-0101', 'Reunión JJ.VV San Bartolomé', 'Margarita Tapia', 'San Bartolomé', 'Aseo y Ornato', '2026-09-01', '2026-09-18', 'En_Proceso', 'Alta', 'Instalación de contenedores.'),
(2, 2, 1, 'CMP-2026-0102', 'Audiencia Vecinos', 'Vecinos Los Olivos', 'Villa Alemania', 'Alumbrado', '2026-08-20', '2026-09-05', 'Pendiente', 'Urgente', 'Reparación de 3 luminarias (Vencido).');

INSERT INTO `indicador_desempeno` (`id_indicador`, `id_usuario`, `id_periodo`, `fecha_calculo`, `porcentaje_ponderado`, `semaforo`, `dias_transcurridos`, `meta_esperada_dia`) VALUES
(1, 1, 1, '2026-09-15', 86.67, 'Verde', 76, 83.52);

INSERT INTO `registro_auditoria` (`id_auditoria`, `id_usuario`, `accion`, `tabla_afectada`, `id_registro_afectado`, `ip_origen`, `datos_previos`, `datos_nuevos`) VALUES
(1, 1, 'REGISTRAR_ACTIVIDAD', 'actividad', 'ACT-2026-0001', '192.168.10.45', NULL, '{"codigo": "ACT-2026-0001"}');
