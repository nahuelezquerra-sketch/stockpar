from decimal import Decimal

from repuesto import Repuesto


def main() -> None:
    repuesto = Repuesto(
        codigo="RP-001",
        nombre="Filtro de aceite",
        precio_compra_usd=Decimal("20.00"),
        margen_ganancia=Decimal("25.00"),
        stock_actual=10,
        stock_minimo=5,
    )

    cotizacion_dolar = Decimal("1400.00")

    precio_venta = repuesto.calcular_precio_venta(
        cotizacion_dolar
    )

    print(f"Código: {repuesto.codigo}")
    print(f"Producto: {repuesto.nombre}")
    print(f"Precio de venta: ${precio_venta}")
    print(f"Stock inicial: {repuesto.stock_actual}")

    repuesto.descontar_stock(2)

    print(
        f"Stock después de la venta: "
        f"{repuesto.stock_actual}"
    )

    if repuesto.requiere_reposicion():
        print("El producto requiere reposición")
    else:
        print("El stock es suficiente")


if __name__ == "__main__":
    main()
