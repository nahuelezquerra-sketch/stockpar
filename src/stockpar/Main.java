package stockpar;

import java.math.BigDecimal;

public class Main {

    public static void main(String[] args) {

        Repuesto repuesto = new Repuesto(
                "RP-001",
                "Filtro de aceite",
                new BigDecimal("20.00"),
                new BigDecimal("25.00"),
                10,
                5
        );

        BigDecimal cotizacionDolar =
                new BigDecimal("1400.00");

        BigDecimal precioVenta =
                repuesto.calcularPrecioVenta(cotizacionDolar);

        System.out.println("Código: " + repuesto.getCodigo());
        System.out.println("Producto: " + repuesto.getNombre());
        System.out.println("Precio de venta: $" + precioVenta);
        System.out.println("Stock inicial: "
                + repuesto.getStockActual());

        repuesto.descontarStock(2);

        System.out.println("Stock después de la venta: "
                + repuesto.getStockActual());

        if (repuesto.requiereReposicion()) {
            System.out.println("El producto requiere reposición");
        } else {
            System.out.println("El stock es suficiente");
        }
    }
}
