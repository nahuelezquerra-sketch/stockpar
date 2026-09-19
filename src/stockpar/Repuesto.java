package stockpar;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class Repuesto {

    private final String codigo;
    private final String nombre;
    private final BigDecimal precioCompraUsd;
    private final BigDecimal margenGanancia;
    private int stockActual;
    private final int stockMinimo;

    public Repuesto(
            String codigo,
            String nombre,
            BigDecimal precioCompraUsd,
            BigDecimal margenGanancia,
            int stockActual,
            int stockMinimo) {

        if (codigo == null || codigo.isBlank()) {
            throw new IllegalArgumentException("El código es obligatorio");
        }

        if (precioCompraUsd.signum() < 0
                || margenGanancia.signum() < 0
                || stockActual < 0
                || stockMinimo < 0) {
            throw new IllegalArgumentException(
                    "Los valores no pueden ser negativos"
            );
        }

        this.codigo = codigo;
        this.nombre = nombre;
        this.precioCompraUsd = precioCompraUsd;
        this.margenGanancia = margenGanancia;
        this.stockActual = stockActual;
        this.stockMinimo = stockMinimo;
    }

    public BigDecimal calcularPrecioVenta(BigDecimal cotizacionDolar) {
        if (cotizacionDolar == null || cotizacionDolar.signum() <= 0) {
            throw new IllegalArgumentException(
                    "La cotización debe ser mayor que cero"
            );
        }

        BigDecimal precioBase =
                precioCompraUsd.multiply(cotizacionDolar);

        BigDecimal porcentaje =
                margenGanancia.divide(new BigDecimal("100"));

        BigDecimal factor =
                BigDecimal.ONE.add(porcentaje);

        return precioBase
                .multiply(factor)
                .setScale(2, RoundingMode.HALF_UP);
    }

    public void descontarStock(int cantidad) {
        if (cantidad <= 0) {
            throw new IllegalArgumentException(
                    "La cantidad debe ser mayor que cero"
            );
        }

        if (cantidad > stockActual) {
            throw new IllegalStateException("Stock insuficiente");
        }

        stockActual -= cantidad;
    }

    public boolean requiereReposicion() {
        return stockActual <= stockMinimo;
    }

    public String getCodigo() {
        return codigo;
    }

    public String getNombre() {
        return nombre;
    }

    public int getStockActual() {
        return stockActual;
    }
}
