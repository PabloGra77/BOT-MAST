from agenda_app import create_app


_startup_error = None

try:
    app = create_app()
except Exception as exc:
    app = None
    _startup_error = exc


def main():
    if _startup_error is not None:
        print(f"\n[ERROR CRITICO AL INICIAR]: {_startup_error}")
        print("Posible causa: Faltan archivos de configuracion o librerias.")
        print("Presione ENTER para salir...")
        input()
        return

    print("Iniciando Bot...")
    print("Por favor no cierre esta ventana.")
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as exc:
        print(f"\n[ERROR CRITICO EN EJECUCION]: {exc}")
        print("Presione ENTER para salir...")
        input()


if __name__ == "__main__":
    main()
