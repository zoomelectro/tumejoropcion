#!/usr/bin/env python3
"""
Gestor de pagos para usuarios Tizen/WebOS por MAC
Uso:
  python gestionar_pagos.py listar
  python gestionar_pagos.py agregar
  python gestionar_pagos.py renovar <mac>
  python gestionar_pagos.py vencidos
  python gestionar_pagos.py online
  python gestionar_pagos.py marcar_online <mac> <true|false>
"""

import json
import sys
import os
from datetime import datetime, timedelta

ARCHIVO = os.path.join(os.path.dirname(__file__), "usuarios.json")

PLANES = {
    "mensual":    30,
    "trimestral": 90,
    "semestral":  180,
    "anual":      365
}

def cargar():
    if not os.path.exists(ARCHIVO):
        return []
    with open(ARCHIVO, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar(data):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Guardado en {ARCHIVO}")

def dias_restantes(fecha_str):
    hoy = datetime.now().date()
    vence = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    return (vence - hoy).days

def estado(dias):
    if dias < 0:   return "VENCIDO"
    if dias <= 7:  return "POR VENCER"
    return "ACTIVO"

def color(texto, dias):
    if dias < 0:   return f"\033[91m{texto}\033[0m"   # rojo
    if dias <= 7:  return f"\033[93m{texto}\033[0m"   # amarillo
    return f"\033[92m{texto}\033[0m"                  # verde

def cmd_listar():
    usuarios = cargar()
    if not usuarios:
        print("No hay usuarios registrados.")
        return
    print(f"\n{'NOMBRE':<20} {'MAC':<20} {'PLATAFORMA':<10} {'VENCIMIENTO':<13} {'DÍAS':<6} {'ESTADO':<12} {'ONLINE'}")
    print("-" * 100)
    for u in sorted(usuarios, key=lambda x: x["vencimiento"]):
        dias = dias_restantes(u["vencimiento"])
        online = "● Online" if u.get("online") else "○ Offline"
        linea = f"{u['nombre']:<20} {u['mac']:<20} {u['plataforma']:<10} {u['vencimiento']:<13} {dias:<6} {estado(dias):<12} {online}"
        print(color(linea, dias))
    print()

def cmd_vencidos():
    usuarios = cargar()
    vencidos = [u for u in usuarios if dias_restantes(u["vencimiento"]) < 0]
    if not vencidos:
        print("✓ No hay usuarios vencidos.")
        return
    print(f"\n{len(vencidos)} usuario(s) vencido(s):\n")
    for u in vencidos:
        dias = dias_restantes(u["vencimiento"])
        print(f"  \033[91m✗\033[0m {u['nombre']:<20} MAC: {u['mac']}  Venció: {u['vencimiento']} ({abs(dias)} días atrás)  Tel: {u.get('telefono','—')}")
    print()

def cmd_online():
    usuarios = cargar()
    online = [u for u in usuarios if u.get("online")]
    print(f"\n{len(online)} usuario(s) conectados ahora:\n")
    for u in online:
        dias = dias_restantes(u["vencimiento"])
        print(color(f"  ● {u['nombre']:<20} MAC: {u['mac']}  Plataforma: {u['plataforma']}  Vence: {u['vencimiento']} ({dias}d)", dias))
    print()

def cmd_agregar():
    print("\n--- Agregar nuevo usuario ---")
    nombre     = input("Nombre completo: ").strip()
    mac        = input("Dirección MAC (XX:XX:XX:XX:XX:XX): ").strip().upper()
    plataforma = input("Plataforma (tizen/webos): ").strip().lower()
    telefono   = input("Teléfono (opcional): ").strip()

    print("Planes disponibles:", ", ".join(PLANES.keys()))
    plan = input("Plan: ").strip().lower()
    if plan not in PLANES:
        print(f"✗ Plan inválido. Opciones: {', '.join(PLANES.keys())}")
        return

    dias_plan = PLANES[plan]
    vencimiento = (datetime.now() + timedelta(days=dias_plan)).strftime("%Y-%m-%d")

    usuarios = cargar()

    # Verificar MAC duplicada
    if any(u["mac"].upper() == mac for u in usuarios):
        print(f"✗ Ya existe un usuario con la MAC {mac}")
        return

    nuevo = {
        "nombre": nombre,
        "mac": mac,
        "plataforma": plataforma,
        "vencimiento": vencimiento,
        "online": False,
        "plan": plan,
        "telefono": telefono
    }
    usuarios.append(nuevo)
    guardar(usuarios)
    print(f"\n✓ Usuario '{nombre}' agregado. Vence el {vencimiento} ({dias_plan} días).")

def cmd_renovar(mac):
    usuarios = cargar()
    usuario = next((u for u in usuarios if u["mac"].upper() == mac.upper()), None)
    if not usuario:
        print(f"✗ No se encontró usuario con MAC {mac}")
        return

    print(f"\nRenovando a: {usuario['nombre']} ({usuario['mac']})")
    print(f"Vencimiento actual: {usuario['vencimiento']}")
    print("Planes disponibles:", ", ".join(PLANES.keys()))
    plan = input("Nuevo plan: ").strip().lower()
    if plan not in PLANES:
        print(f"✗ Plan inválido.")
        return

    dias_plan = PLANES[plan]
    # Si está vencido, renovar desde hoy; si no, extender desde la fecha actual
    hoy = datetime.now().date()
    actual = datetime.strptime(usuario["vencimiento"], "%Y-%m-%d").date()
    base = max(hoy, actual)
    nuevo_venc = (base + timedelta(days=dias_plan)).strftime("%Y-%m-%d")

    usuario["vencimiento"] = nuevo_venc
    usuario["plan"] = plan
    guardar(usuarios)
    print(f"\n✓ Renovado. Nuevo vencimiento: {nuevo_venc}")

def cmd_marcar_online(mac, estado_str):
    usuarios = cargar()
    usuario = next((u for u in usuarios if u["mac"].upper() == mac.upper()), None)
    if not usuario:
        print(f"✗ No se encontró usuario con MAC {mac}")
        return
    online = estado_str.lower() in ("true", "1", "si", "yes")
    usuario["online"] = online
    guardar(usuarios)
    estado_txt = "Online" if online else "Offline"
    print(f"✓ {usuario['nombre']} marcado como {estado_txt}")

def cmd_resumen():
    usuarios = cargar()
    total    = len(usuarios)
    online   = sum(1 for u in usuarios if u.get("online"))
    vencidos = sum(1 for u in usuarios if dias_restantes(u["vencimiento"]) < 0)
    proximos = sum(1 for u in usuarios if 0 <= dias_restantes(u["vencimiento"]) <= 7)
    activos  = total - vencidos

    print("\n╔══════════════════════════════╗")
    print("║   RESUMEN DEL PANEL IPTV     ║")
    print("╠══════════════════════════════╣")
    print(f"║  Total usuarios:   {total:<10}║")
    print(f"║  Activos:          \033[92m{activos:<10}\033[0m║")
    print(f"║  Online ahora:     \033[92m{online:<10}\033[0m║")
    print(f"║  Vencen en 7 días: \033[93m{proximos:<10}\033[0m║")
    print(f"║  Vencidos:         \033[91m{vencidos:<10}\033[0m║")
    print("╚══════════════════════════════╝\n")

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "listar":
        cmd_resumen()
        cmd_listar()
    elif args[0] == "vencidos":
        cmd_vencidos()
    elif args[0] == "online":
        cmd_online()
    elif args[0] == "agregar":
        cmd_agregar()
    elif args[0] == "renovar":
        if len(args) < 2:
            print("Uso: python gestionar_pagos.py renovar <mac>")
        else:
            cmd_renovar(args[1])
    elif args[0] == "marcar_online":
        if len(args) < 3:
            print("Uso: python gestionar_pagos.py marcar_online <mac> <true|false>")
        else:
            cmd_marcar_online(args[1], args[2])
    elif args[0] == "resumen":
        cmd_resumen()
    else:
        print(__doc__)
