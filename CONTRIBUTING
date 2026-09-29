# Cómo trabajamos

Léelo antes de tu primer commit. Son diez minutos y evitan la mayor parte de los problemas que aparecen cuando cinco personas tocan el mismo código.

---

## 1. Antes de empezar

- [ ] Acepta la invitación a la organización de GitHub.
- [ ] Clona el repositorio y levanta el proyecto en local siguiendo el README.
- [ ] Pide acceso al gestor de contraseñas compartido.
- [ ] Abre el proyecto `AKASH` en Jira y ubica las historias del sprint actual.

---

## 2. Ramas

Nunca trabajes sobre `main`. Cada historia va en su propia rama, nombrada con el código de la historia:

```
feature/HU014-registrar-producto
feature/HU027-variantes
fix/HU003-stock-negativo
```

El código de la historia en el nombre no es un capricho: permite leer el repositorio contra el backlog, que es la trazabilidad que el curso evalúa.

```bash
git checkout main
git pull
git checkout -b feature/HU014-registrar-producto
```

> **Nota:** la protección de rama no se puede activar porque el repositorio es privado y la organización está en el plan gratuito de GitHub. Técnicamente `main` está desprotegida, así que esto funciona **por acuerdo**. Respétalo.

---

## 3. Commits

Un commit por cambio con sentido propio, citando la historia:

```
HU014: agrega endpoint POST /admin/productos
HU014: valida que el precio sea obligatorio
HU027: corrige herencia de precio en variantes
```

Evita los commits del tipo `cambios`, `avance`, `fix` o `asdasd`. En la Sprint Review el docente puede abrir el historial, y un historial legible dice más del equipo que cualquier explicación.

---

## 4. Pull requests

Cuando termines tu tarea, sube la rama y abre un pull request contra `main`.

```bash
git push -u origin feature/HU014-registrar-producto
```

**Título:** el código de la historia y qué hace.
`HU014: registrar un producto nuevo`

**Descripción:** usa esta plantilla.

```markdown
## Historia
HU014 — Registrar un producto nuevo (AKASH-7)

## Qué hace
Breve descripción de lo que se construyó.

## Escenarios de aceptación cubiertos
- [ ] Escenario 1 — Registro completo
- [ ] Escenario 2 — Campos obligatorios vacíos
- [ ] ...

## Cómo probarlo
Pasos para que quien revise pueda verificarlo.

## Pendiente
Lo que quedó fuera, si aplica.
```

**Reglas:**

- Necesita la aprobación de **otro integrante** antes de fusionar.
- Quien revisa no solo lee el código: verifica que los escenarios de aceptación se cumplan.
- Si lleva más de dos días abierto, algo está mal. Avísalo en la daily.
- Después de fusionar, borra la rama.

---

## 5. Definición de Terminado

Una historia está terminada cuando cumple las ocho condiciones acordadas en el Sprint 0:

1. Todos sus escenarios de aceptación se verifican sobre la aplicación en ejecución.
2. El código está integrado a la rama principal y revisado por al menos otro integrante.
3. Funciona en el entorno desplegado, accesible desde un equipo ajeno al del desarrollador.
4. Opera correctamente en pantalla de celular.
5. Funciona con datos representativos reales de Akash Store, no con datos de relleno.
6. No introduce regresiones en las historias ya entregadas.
7. Está trazada a la fuente de elicitación que la originó.
8. Fue aceptada por el Product Owner en la Sprint Review.

El punto 5 es el que más se olvida: nada de "Producto 1", "Producto 2". Se usa el catálogo real de la tienda.

---

## 6. El tablero de Jira

Mueve tu tarjeta cuando cambies de estado, no al final del sprint. Las columnas corresponden a la Definición de Terminado:

| Columna | Qué significa |
|---|---|
| Por hacer | Comprometida en el sprint, sin empezar |
| En curso | La estás construyendo |
| En revisión | Pull request abierto, esperando aprobación |
| Desplegado | Funciona en el entorno desplegado y verificaste sus escenarios ahí |
| Listo | Aceptada por el Product Owner en la Sprint Review |

Durante el sprint casi nada llega a **Listo**: las historias se acumulan en **Desplegado** hasta la review. Es lo correcto, aunque al inicio resulte raro.

---

## 7. Seguridad

**Ninguna credencial en el repositorio.** Contraseñas, cadenas de conexión, llaves de Supabase y el `JWT_SECRET` van en variables de entorno y en el gestor compartido.

Antes de cada commit, revisa qué estás subiendo:

```bash
git diff --staged
```

Si subiste un secreto por accidente, **avísalo de inmediato**: no basta con borrarlo en el siguiente commit, porque queda en el historial y hay que rotar la credencial.

**Datos de clientas.** El sistema va a manejar nombres, teléfonos y direcciones de personas reales. Esa información no se copia a capturas, ni a documentos, ni a datos de prueba.

---

## 8. Pruebas

- Quien escribe un endpoint escribe sus pruebas con pytest. No se delegan.
- Antes de abrir el pull request, corre la suite completa:

```bash
cd backend && pytest
```

- QA verifica los escenarios de aceptación **en celular y sobre el entorno desplegado**, no en local. La rúbrica evalúa que el producto funcione fuera de la máquina de quien lo programó.

---

## 9. Si te bloqueas

Dilo en la daily o en el grupo el mismo día, no al final del sprint. Un impedimento reportado a tiempo lo resuelve el Scrum Master; uno callado se convierte en una historia sin terminar.

Los impedimentos se registran en Jira con la etiqueta `impedimento`, con responsable y estado. En la exposición hay que poder abrir ese registro.

---

## 10. A quién preguntarle

| Tema | Persona |
|---|---|
| Qué se construye, prioridades, alcance | Product Owner |
| Accesos, impedimentos, ceremonias | Scrum Master |
| Dudas sobre una historia o su criterio de aceptación | Product Owner |
| Cualquier cosa que quiera saber la propietaria | Product Owner, que es el único interlocutor con ella |

Ese último punto importa: si la propietaria le pide algo directamente a alguien del equipo, se canaliza por el Product Owner. Si no, aparecen requisitos que nadie priorizó.
