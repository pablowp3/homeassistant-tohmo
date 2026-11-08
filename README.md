# Tohmo para Home Assistant

Integración para controlar un cargador Alfen gestionado por la nube española de
Tohmo, antes ChargeGuru. Utiliza la cuenta de la app Android y no necesita acceder
a la red local del cargador.

## Para qué sirve cada entidad

La instalación verificada tiene **23 entidades**: 6 botones, 4 interruptores,
2 ajustes numéricos, 1 selector, 1 campo de texto y 9 sensores. Una entidad es cada
control o dato que puedes añadir a un panel o utilizar en una automatización.
Estos son sus nombres en español; Home Assistant puede añadir el nombre del cargador.

Los controles requieren que Tohmo reconozca la cuenta como propietaria. Solo se
ofrecen los ajustes compatibles con el equipo y permitidos por el operador. Si
falla la consulta a la nube, pueden aparecer como **No disponible**. Un dato que
Tohmo no proporciona aparece como **Desconocido**, sin sustituirlo por cero.

### Botones: órdenes puntuales

Un botón envía una orden una vez. Su fecha de última pulsación no confirma que
el equipo haya terminado de ejecutarla: comprueba después el estado.

| Botón | Qué hace y cuándo está disponible |
|---|---|
| **Iniciar sesión de carga** | Solicita una nueva sesión en el conector. Se deshabilita si ya hay una sesión abierta o el estado no permite iniciar. El coche y el cargador determinan cuándo empieza a circular energía. |
| **Detener sesión de carga** | Solicita finalizar la sesión abierta, incluso si está suspendida a 0 W. Requiere que Tohmo permita la parada remota; se deshabilita cuando la sesión ya está deteniéndose. |
| **Reiniciar cargador** | Reinicia el equipo físico, lo que puede interrumpir temporalmente su funcionamiento o conexión. No reinicia Home Assistant. Se deshabilita mientras el equipo está reiniciándose; no se bloquea por tener una sesión activa. |
| **Desbloquear conector** | Solicita liberar el cable en el lado del cargador, si es compatible. Es una orden puntual: no cambia el ajuste **Bloquear conector** ni envía una parada. Tohmo puede rechazarla según el estado del equipo. |
| **Buscar actualización de firmware** | Consulta si Tohmo ofrece una actualización del programa interno del cargador. No instala nada. Muestra el resultado en **Actualización de firmware** y solo existe en equipos compatibles. |
| **Instalar actualización de firmware** | Vuelve a consultar la disponibilidad y solicita instalar si la consulta tiene éxito. Puede dejar el equipo temporalmente fuera de servicio. Se deshabilita mientras hay una sesión abierta o una actualización en curso. |

### Interruptores y ajustes

| Entidad | Tipo | Qué significa o qué cambia |
|---|---|---|
| **Sesión de carga** | Interruptor | Encendido significa que Tohmo mantiene una sesión abierta. Encenderlo equivale a **Iniciar sesión de carga** y apagarlo a **Detener sesión de carga**, con las mismas comprobaciones. No indica necesariamente consumo ni corta la alimentación del equipo. |
| **Exigir autenticación** | Interruptor | Activado exige autorizar el inicio, como la confirmación en la app. Desactivado puede permitir que la carga comience al conectar el coche sin confirmación. Cambia la autorización del cargador, no el acceso a Home Assistant. Solo aparece si el operador permite modificarla. |
| **Mantener vehículo despierto** | Interruptor | Activa el ajuste que ofrece continuamente la corriente mínima durante esperas de una carga programada o retrasada, para evitar que el coche se duerma. Su efecto depende del vehículo y de Tohmo. No crea horarios ni habilita la carga programada, desactivada en la cuenta verificada. |
| **Bloquear conector** | Interruptor | Activa o desactiva el ajuste persistente de bloqueo del cable en el lado del cargador; no controla el cierre del puerto del coche. Solo aparece en equipos compatibles. Tohmo puede rechazar cambiarlo durante una sesión. |
| **Corriente máxima de carga** | Número, **A** | Fija el límite de corriente solicitado al cargador. El coche puede consumir menos. Admite amperios enteros dentro de los límites comunicados por Tohmo; en el equipo verificado, **6–16 A**. Requiere que el equipo permita regularla. |
| **Corriente de mantenimiento** | Número, **A** | Configura la corriente mínima usada por **Mantener vehículo despierto** cuando está activado. Debe respetar los límites de Tohmo y no superar la corriente máxima. No es un ajuste de mantenimiento de la batería de 12 V. |
| **Intensidad del LED** | Selector | Cambia la iluminación del cargador: **5 = baja**, **20 = media**, **50 = alta**. Son valores de configuración, no medidas de consumo. Solo aparece si el equipo admite el ajuste. |
| **Nombre del cargador** | Texto | Cambia el nombre guardado en Tohmo y utilizado por la integración; no es solo una etiqueta local. No puede quedar vacío. Renombrar no inicia ni detiene una sesión. |

Los dos valores de corriente y **Mantener vehículo despierto** se guardan juntos,
conservando los otros valores recién consultados al modificar uno. Para reducir
la corriente máxima por debajo de la de mantenimiento, reduce primero esta última.
El efecto físico de mantener el coche despierto todavía no se ha probado en esta cuenta.

El LED puede tener un valor previo como **100**: se muestra y se puede conservar.
Tras elegir 5, 20 o 50, no se ofrece restaurar 100 porque esa operación no está
verificada. La app agrupa valores superiores a 20 como «alta», pero guarda 50.

### Sensores: información de solo lectura

Estos nueve sensores no envían órdenes. Los datos de sesión corresponden a la
sesión que devuelve Tohmo; si deja de devolverla, pueden quedar como **Desconocido**.

| Sensor | Qué muestra y cómo interpretarlo |
|---|---|
| **Estado del conector** | Estado del equipo, por ejemplo `charging` (cargando), `suspended` (carga suspendida) o `available` (disponible). No confirma por sí solo que la sesión esté cerrada. |
| **Estado de la sesión** | Estado en Tohmo, por ejemplo `active` (activa), `stopping` (deteniéndose) o `finished` (finalizada). Puede seguir activo con el conector suspendido. |
| **Potencia de carga** | Potencia comunicada para la sesión, en **W**. Indica la velocidad de carga en esa lectura; 1000 W = 1 kW. Un valor de 0 W no cierra la sesión. |
| **Energía de la sesión** | Energía acumulada en esa sesión, en **Wh**; 1000 Wh = 1 kWh. Puede cambiar o reiniciarse con otra sesión. No debe tratarse como un contador histórico acumulativo del cargador. |
| **Duración de la sesión** | Duración comunicada por Tohmo, en segundos (**s**). No se calcula sumando solo los instantes con potencia positiva, por lo que no equivale necesariamente a tiempo de carga efectiva. |
| **Coste de la sesión** | Importe comunicado por Tohmo, en la moneda de la sesión, por ejemplo **EUR**. La integración no calcula una tarifa propia ni realiza un cobro. |
| **Energía del mes anterior** | Total del mes anterior comunicado por Tohmo, en **kWh**. Es un resumen mensual del cargador, distinto de la energía de una sesión y de un contador histórico. |
| **Versión de firmware** | Versión instalada del programa interno del cargador. No corresponde a la versión de esta integración. |
| **Actualización de firmware** | **Disponible** tras una búsqueda satisfactoria; **Instalando** si Tohmo indica una actualización en curso. **Desconocido** antes de consultar, tras reiniciar la integración o si falla la consulta. Desconocido no significa «al día». |

**Una sesión activa puede estar suspendida y consumir 0 W.** El coche puede dejar
de pedir energía sin que la sesión termine. El interruptor **Sesión de carga**
permanece encendido hasta que Tohmo comunica su finalización.

El resultado de firmware **Disponible** refleja la última búsqueda, no una
comprobación continua. Instalar vuelve a consultar primero; buscar no instala.

## Actualización de datos y límites

Los datos se consultan cada **60 segundos**, antes de cada orden y después de
una orden aceptada. Los cambios pueden tardar en llegar desde la nube; la
integración muestra lo que comunica Tohmo, sin suponer que una orden funcionó.

Antes de actuar se revisan permisos, límites y estado. No se permite iniciar
otra sesión mientras una siga abierta ni repetir una parada ya en curso. Para
iniciar se admiten `ready`, `available`, `occupied`, `preparing` y `finishing`,
siempre sin sesión abierta. Un control visible puede ser rechazado si el estado
cambió o Tohmo impide la operación.

Una orden que agota el tiempo de espera puede haber llegado al cargador. No se
reenvía automáticamente: comprueba el estado antes de decidir si la repites.

En la cuenta verificada están desactivados horarios y carga inteligente, solar,
acceso compartido, reembolsos y AxleFlex. Esta versión no ofrece esas funciones
ni un botón separado de pausa/reanudación. Consulta el
[inventario técnico y sus evidencias](docs/API.md) para conocer el alcance completo.

## Instalación mediante Marketplace

El repositorio es público y no contiene datos de cuentas. Se añade por enlace;
no necesita estar en el catálogo predeterminado.
[Guía oficial de Marketplace](https://www.home-assistant.io/integrations/marketplace/).

1. Abre **Ajustes → Marketplace → Añadir desde un enlace** (*Add from link*).
2. Introduce `https://github.com/pablowp3/homeassistant-tohmo` y selecciona
   **Integración** si solicita una categoría.
3. Abre **Tohmo**, instala y reinicia Home Assistant cuando lo indique.
4. Ve a **Ajustes → Dispositivos y servicios → Añadir integración → Tohmo**.
5. Introduce el correo y la contraseña de tu cuenta de la app Android de Tohmo.

Con HACS en versiones anteriores, añade el mismo enlace en **Repositorios
personalizados**, categoría **Integración**, descarga y reinicia.

**Alternativa manual:** copia `custom_components/tohmo` del repositorio a
`/config/custom_components/tohmo` en Home Assistant. Reinicia y sigue los pasos 4–5.

La contraseña se usa para iniciar sesión y no se guarda. Home Assistant almacena
credenciales temporales de acceso y renovación, que se renuevan automáticamente.
Si Tohmo revoca el acceso, solicita iniciar sesión de nuevo. Mantén privadas las
copias de seguridad de Home Assistant, porque contienen esos datos de acceso.

## Estado de las pruebas

La versión **0.1.1** está instalada mediante Marketplace en Home Assistant
**2026.11.0**, con Python **3.14.10**. Se verificaron configuración, autenticación,
lectura de datos y las **23 entidades**, con unidades y límites correctos y sin
errores de Tohmo en el registro después del reinicio.

Pasan las **30 pruebas automatizadas**. La versión 0.1.1 corrige un error real en
los sensores de diagnóstico de firmware; las pruebas reproducen el fallo anterior
y comprueban las unidades corregidas.

Las órdenes físicas de inicio, parada, ajustes y firmware siguen sin probarse en
el equipo real. Tampoco se ejecutó la búsqueda opcional de firmware. Los efectos
descritos se basan en la app y las órdenes implementadas; su ejecución depende de
Tohmo y del cargador. Véase [el estado detallado de validación](docs/HANDOFF.md).

Es una integración no oficial que utiliza la interfaz interna de la app móvil;
Tohmo puede cambiarla o retirarla. No utiliza el portal francés de clientes ni el
portal de administración del operador.

## Desarrollo

Las pruebas independientes requieren Python 3.12 o posterior. La integración
instalada utiliza el Python incluido en Home Assistant.

```sh
python -m pip install aiohttp
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Las pruebas usan datos ficticios. No publiques respuestas reales de cuentas,
contraseñas, credenciales de acceso o renovación, identificadores del cargador,
datos de facturación, APK ni XAPK.
