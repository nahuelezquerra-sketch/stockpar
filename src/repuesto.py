from decimal import Decimal, ROUND_HALF_UP


class Repuesto:
    def __init__(
        self,
        codigo: str,
        nombre: str,
        precio_compra_usd: Decimal,
        margen_ganancia: Decimal,
        stock_actual: int,
        stock_minimo: int,
    ):
        if not codigo.strip():
            raise ValueError("El código es obligatorio")

        if (
            precio_compra_usd < 0
            or margen_ganancia < 0
            or stock_actual < 0
            or stock_minimo < 0
        ):
            raise ValueError("Los valores no pueden ser negativos")

        self.codigo = codigo
        self.nombre = nombre
        self.precio_compra_usd = precio_compra_usd
        self.margen_ganancia = margen_ganancia
        self.stock_actual = stock_actual
        self.stock_minimo = stock_minimo

    def calcular_precio_venta(
        self,
        cotizacion_dolar: Decimal,
    ) -> Decimal:
        if cotizacion_dolar <= 0:
            raise ValueError(
                "La cotización debe ser mayor que cero"
            )

        precio_base = (
            self.precio_compra_usd * cotizacion_dolar
        )

        factor_ganancia = (
            Decimal("1")
            + self.margen_ganancia / Decimal("100")
        )

        precio_venta = precio_base * factor_ganancia

        return precio_venta.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def descontar_stock(self, cantidad: int) -> None:
        if cantidad <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero"
            )

        if cantidad > self.stock_actual:
            raise ValueError("Stock insuficiente")

        self.stock_actual -= cantidad

    def requiere_reposicion(self) -> bool:
        return self.stock_actual <= self.stock_minimo
