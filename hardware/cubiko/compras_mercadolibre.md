# Lista de compras (Mercado Libre México): tarjeta Cubiko

Supone que ya tienes la Raspberry Pi 5, las 2 ESP32 DevKit V1, los 3 L298N, los 6 Pololu 37D, los servos y la batería.

**Cómo usar los links:**
- La mayoría son **búsquedas** en Mercado Libre, porque las publicaciones cambian o se agotan. Elige la que tenga buenas calificaciones y revisa en la ficha el paso, la cantidad de piezas y el voltaje.
- Las 2 publicaciones específicas (el step-down y el kit de V-bits) se tomaron del buscador en noviembre de 2026.

## 1. Componentes de la tarjeta

| Qué | Cantidad | Dónde comprar | Notas |
|---|---|---|---|
| Kit de resistencias 1/4 W 1 % | 1 kit (ocupas 10k ×7, 20k ×6, 1k ×4, 100k, 27k, 2.2k, 330, 470) | [búsqueda](https://listado.mercadolibre.com.mx/kit-resistencias-1-4w-1-porciento) | Revisa que el kit traiga 20k y 27k |
| Capacitor cerámico 1 nF (102) | 6 | [búsqueda](https://listado.mercadolibre.com.mx/capacitor-ceramico-102-1nf) | Paso 2.5 mm |
| Capacitor cerámico 100 nF (104) | 1 | [búsqueda](https://listado.mercadolibre.com.mx/capacitor-ceramico-104-100nf) | Paso 5 mm |
| Electrolítico 1000 µF 16 V, Ø10 mm | 3 | [búsqueda](https://listado.mercadolibre.com.mx/capacitor-electrolitico-1000uf-16v) | Cuerpo de Ø10 mm exacto (10×13 a 10×20) y paso de 5 mm; los de Ø8 mm traen paso de 3.5 mm y no coinciden |
| Diodo TVS SA5.0A | 1 | [búsqueda](https://listado.mercadolibre.com.mx/diodo-tvs-sa5.0a) | Protección del 5 V de la Pi |
| Diodo Schottky 1N5819 | 2 | [búsqueda](https://listado.mercadolibre.com.mx/diodo-schottky-1n5819) | |
| LEDs de 5 mm: rojo, verde y azul | 1 de cada uno | [búsqueda](https://listado.mercadolibre.com.mx/kit-leds-5mm-colores) | |
| Header hembra 2x20 (GPIO de la Pi) | 1 | [búsqueda](https://listado.mercadolibre.com.mx/header-hembra-2x20-raspberry) | Con Active Cooler en la Pi, busca uno **alto** (stacking / 15 mm) |
| Tira header hembra 1x40, 2.54 mm | 2 (salen los 4 zócalos 1x15 de las ESP32) | [búsqueda](https://listado.mercadolibre.com.mx/tira-header-hembra-1x40-2.54) | |
| Tira header macho 1x40, 2.54 mm | 2 (8 servos de 1x3 + pines para las 41 vías) | [búsqueda](https://listado.mercadolibre.com.mx/tira-header-macho-1x40) | En lugar de pines para las vías también sirve alambre de 0.8 mm |
| Bornera KF350 paso 3.5 mm, 2 y 3 vías (encastrables) | 5 de 3 vías y 8 de 2 vías | [búsqueda KF350](https://listado.mercadolibre.com.mx/bornera-kf350-3.5mm) | Se ensamblan entre sí: 7 vías = 3+2+2 (×3, L298N) y 5 vías = 3+2 (×2, encoders) |
| Bornera KF301 paso 5.08 mm, 2 vías | 3 (5 V, servos, batería) | [búsqueda](https://listado.mercadolibre.com.mx/bornera-kf301-2-pines-5.08) | |
| Separadores M2.5 y tornillos (para la Pi) | 4 | [búsqueda](https://listado.mercadolibre.com.mx/separadores-m2.5-raspberry) | 11 mm sin cooler; 16–18 mm con Active Cooler |
| Separadores M3 y tornillos (al chasis) | 4 | [búsqueda](https://listado.mercadolibre.com.mx/separadores-latón-m3) | |

## 2. Alimentación y arnés

| Qué | Cantidad | Dónde comprar | Notas |
|---|---|---|---|
| Step-down 12 V → 5 V 5 A, salida fija | 1 | [publicación](https://www.mercadolibre.com.mx/convertidor-buck-12v-24v-a-5v-5a-voltaje-fuente-de/p/MLM2012812928) · [búsqueda](https://listado.mercadolibre.com.mx/step-down-5v) | Alternativa: [XL4015 ajustable](https://listado.mercadolibre.com.mx/regulador-xl4015), con disipador y ajustado con multímetro **antes** de conectar la Pi |
| Regulador / BEC 12 V → 6 V, ≥ 10 A | 1 | [búsqueda](https://listado.mercadolibre.com.mx/regulador-de-voltaje-a-6v-5a) · [UBEC](https://listado.mercadolibre.com.mx/ubec) | Confirma que la ficha diga **10 A** (hay versiones de 5 A) |
| Portafusible ATO en línea + fusibles de 15 A | 1 + 3 | [búsqueda](https://listado.mercadolibre.com.mx/portafusible-ato-en-linea) | |
| Conectores XT60 (macho y hembra) | 2 pares | [búsqueda](https://listado.mercadolibre.com.mx/conector-xt60) | |
| Cable de silicón 14–16 AWG, rojo y negro | 2 m | [búsqueda](https://listado.mercadolibre.com.mx/cable-silicon-14-awg) | Batería → fusible → L298N, step-down y BEC |
| Cable de 22 AWG multicolor | 1 rollo o kit | [búsqueda](https://listado.mercadolibre.com.mx/cable-calibre-22-kit-colores) | Bornas de la tarjeta → L298N y encoders |
| Bloque de distribución / terminal de tierra | 1 | [búsqueda](https://listado.mercadolibre.com.mx/bloque-distribucion-terminales) | El negativo común en estrella |

## 3. Para fresar en la Cubiko

| Qué | Cantidad | Dónde comprar | Notas |
|---|---|---|---|
| Placa fenólica (FR1) **doble cara** 10 × 15 cm | 2 o 3 (una de prueba) | [búsqueda](https://listado.mercadolibre.com.mx/placa-fenolica-doble-cara-10x15) | Mejor FR1 que FR4: su polvo no es fibra de vidrio |
| Fresa en V 20°, punta 0.1 mm, zanco 1/8" | 1 kit | [kit de 20/30/40/60°](https://articulo.mercadolibre.com.mx/MLM-939206950-kit-4-cortadores-v-20-30-40-60-grados-pcb-router-cnc-_JM) · [búsqueda](https://listado.mercadolibre.com.mx/fresa-en-v-pcb) | Es la que usa por defecto el Fab Lab: 20° × 0.1 a 0.1 mm de profundidad |
| Brocas para PCB 0.8 / 1.0 / 1.2 mm, zanco 3.175 mm | 1 juego | [búsqueda](https://listado.mercadolibre.com.mx/brocas-pcb-3.175mm) | El flujo del Fab Lab usa solo la de 1.0 para todos los agujeros de 0.6 a 1.3 mm |
| Fresa tipo maíz (corn) de 1.0 mm o plana de 2 mm | 1–2 | [búsqueda](https://listado.mercadolibre.com.mx/fresa-maiz-1mm-pcb) | Para el contorno y los barrenos grandes |
| Pasadores de acero de Ø3 mm | 2 | [búsqueda](https://listado.mercadolibre.com.mx/pasador-acero-3mm) | Pines de alineación para voltear la placa; sirven zancos de brocas de 3 mm rotas |
| Cinta doble cara delgada | 1 rollo | [búsqueda](https://listado.mercadolibre.com.mx/cinta-doble-cara-delgada) | Para pegar la placa al martir |
| Martir de MDF de 6 mm | 1 | [búsqueda](https://listado.mercadolibre.com.mx/mdf-6mm-corte) | |
