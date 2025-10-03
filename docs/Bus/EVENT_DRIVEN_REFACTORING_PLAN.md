# Plan de Refactorización: Arquitectura Event-Driven

## 🎯 Objetivo General

Transformar la aplicación BFF de una arquitectura monolítica con alto acoplamiento a una arquitectura event-driven que permita:

- **Desacoplamiento de dominios**: Eliminar las 80+ dependencias cruzadas actuales
- **Comunicación asíncrona**: Implementar un Event Bus centralizado
- **Escalabilidad**: Facilitar el crecimiento y mantenimiento del sistema
- **Testabilidad**: Mejorar la capacidad de testing unitario e integración

## 📊 Estado Actual vs Estado Objetivo

### Estado Actual (Problemático)
- **80+ imports cruzados** entre apps (stock ↔ pos ↔ catalog ↔ orders ↔ customers)
- **Comunicación síncrona directa** entre dominios
- **Alto acoplamiento** que dificulta cambios y testing
- **Infraestructura de eventos limitada** (solo notificaciones básicas)

### Estado Objetivo
- **<5 imports cruzados** entre dominios
- **Event Bus centralizado** para comunicación
- **Eventos de dominio estructurados** con contratos claros
- **Handlers desacoplados** que reaccionan a eventos
- **Interfaces bien definidas** entre dominios

## 🏗️ Arquitectura Event-Driven Propuesta

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   POS Domain    │    │  Stock Domain   │    │ Catalog Domain  │
│                 │    │                 │    │                 │
│ • API           │    │ • Models        │    │ • Models        │
│ • Services      │    │ • Services      │    │ • Pricing       │
│ • Models        │    │ • FEFO Logic    │    │ • Utils         │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ publish events       │ publish events       │ publish events
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      EVENT BUS            │
                    │                           │
                    │ • Event Publishing        │
                    │ • Event Subscription      │
                    │ • Event Routing           │
                    │ • Correlation Tracking    │
                    │ • Error Handling          │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │ subscribe to events   │ subscribe to events   │ subscribe to events
          │                       │                       │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│ Orders Domain   │    │Customers Domain │    │Notifications    │
│                 │    │                 │    │                 │
│ • Order Logic   │    │ • Customer Mgmt │    │ • Alerts        │
│ • Checkout      │    │ • Profiles      │    │ • Email/SMS     │
│ • Delivery      │    │ • Preferences   │    │ • Rate Limiting │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Plan de Implementación - 8 Fases

### **Fase 1: Análisis y Mapeo** (Semana 1)
**Objetivo**: Entender completamente el estado actual

#### Tareas:
- [ ] Mapear todas las dependencias cruzadas actuales
- [ ] Identificar flujos críticos de datos entre dominios
- [ ] Documentar casos de uso principales
- [ ] Analizar patrones de comunicación existentes
- [ ] Crear matriz de dependencias

#### Entregables:
- Documento de análisis de dependencias
- Diagrama de flujos críticos
- Lista priorizada de casos de uso

---

### **Fase 2: Diseño de Eventos y Contratos** (Semana 2)
**Objetivo**: Definir la estructura de eventos y interfaces

#### Tareas:
- [ ] Diseñar eventos de dominio para cada app
- [ ] Definir contratos de eventos (schemas)
- [ ] Establecer convenciones de naming
- [ ] Crear documentación de eventos
- [ ] Validar cobertura de casos de uso

#### Eventos Principales:
```python
# Stock Events
- StockUpdated(product_id, old_qty, new_qty, warehouse_id)
- LowStockDetected(product_id, current_qty, threshold)
- StockReserved(product_id, qty, order_id)
- StockReleased(product_id, qty, order_id)

# Order Events  
- OrderCreated(order_id, customer_id, items)
- OrderConfirmed(order_id, total_amount)
- OrderCancelled(order_id, reason)
- OrderDelivered(order_id, delivery_date)

# POS Events
- SaleCompleted(sale_id, items, customer_id, total)
- PaymentProcessed(sale_id, amount, method)

# Catalog Events
- ProductUpdated(product_id, changes)
- PriceChanged(product_id, old_price, new_price)
- BenefitActivated(benefit_id, conditions)
```

#### Entregables:
- Especificación completa de eventos
- Documentación de contratos
- Diagramas de flujo de eventos

---

### **Fase 3: Infraestructura Base** (Semana 3)
**Objetivo**: Implementar el Event Bus y componentes core

#### Tareas:
- [ ] Crear `apps/core/events.py` - Event Bus centralizado
- [ ] Implementar clases base para eventos
- [ ] Crear sistema de handlers
- [ ] Implementar middleware de correlación
- [ ] Agregar logging y monitoring
- [ ] Crear tests unitarios de infraestructura

#### Componentes:
```python
# apps/core/events.py
class DomainEvent(ABC)
class EventBus
class EventHandler(ABC)
class EventMiddleware
class CorrelationTracker
```

#### Entregables:
- Event Bus funcional
- Tests de infraestructura
- Documentación técnica

---

### **Fase 4: Migración Piloto - Stock Domain** (Semana 4)
**Objetivo**: Migrar Stock como caso piloto

#### Tareas:
- [ ] Crear `apps/stock/events.py` - Eventos específicos
- [ ] Crear `apps/stock/event_handlers.py` - Handlers
- [ ] Modificar `stock/services.py` para publicar eventos
- [ ] Implementar handlers para eventos externos
- [ ] Crear tests de integración
- [ ] Validar funcionamiento end-to-end

#### Eventos Implementados:
- Stock quantity changes
- Low stock alerts
- Reservation events
- FEFO allocation events

#### Entregables:
- Stock domain event-driven
- Tests pasando
- Métricas de performance

---

### **Fase 5: Migración POS y Eliminación de Imports** (Semana 5)
**Objetivo**: Migrar POS y empezar a eliminar dependencias directas

#### Tareas:
- [ ] Crear eventos POS
- [ ] Migrar `pos/api.py` para usar eventos
- [ ] Eliminar imports directos de stock en POS
- [ ] Implementar handlers POS
- [ ] Actualizar tests POS
- [ ] Validar funcionalidad completa

#### Imports Eliminados:
```python
# ANTES (pos/api.py)
from apps.stock.services import allocate_lots_fefo, record_exit_fefo
from apps.stock.models import StockLot

# DESPUÉS
# Solo eventos - sin imports directos
```

#### Entregables:
- POS completamente event-driven
- Reducción significativa de imports
- Tests actualizados

---

### **Fase 6: Migración Dominios Restantes** (Semana 6)
**Objetivo**: Migrar Orders, Catalog, Customers

#### Tareas:
- [ ] Migrar Orders domain
- [ ] Migrar Catalog domain  
- [ ] Migrar Customers domain
- [ ] Actualizar Notifications para usar eventos
- [ ] Eliminar imports cruzados restantes
- [ ] Crear tests de integración completos

#### Dominios Migrados:
- **Orders**: Checkout, delivery, picking
- **Catalog**: Pricing, benefits, product updates
- **Customers**: Profile updates, preferences
- **Notifications**: Event-driven alerts

#### Entregables:
- Todos los dominios event-driven
- <5 imports cruzados restantes
- Suite completa de tests

---

### **Fase 7: Testing Integral y Validación** (Semana 7)
**Objetivo**: Validar el sistema completo

#### Tareas:
- [ ] Tests end-to-end completos
- [ ] Performance testing
- [ ] Load testing del Event Bus
- [ ] Validación de casos edge
- [ ] Monitoring y alertas
- [ ] Documentación de troubleshooting

#### Validaciones:
- Todos los flujos críticos funcionando
- Performance igual o mejor
- Error handling robusto
- Monitoring efectivo

#### Entregables:
- Sistema completamente validado
- Documentación de operaciones
- Playbooks de troubleshooting

---

### **Fase 8: Cleanup y Documentación** (Semana 8)
**Objetivo**: Finalizar y documentar

#### Tareas:
- [ ] Cleanup de código legacy
- [ ] Documentación completa de arquitectura
- [ ] Guías de desarrollo
- [ ] Training para el equipo
- [ ] Métricas finales
- [ ] Plan de mantenimiento

#### Entregables:
- Código limpio y documentado
- Arquitectura completamente event-driven
- Equipo capacitado
- Métricas de éxito alcanzadas

## 📈 Métricas de Éxito

### Métricas Cuantitativas:
- **Imports cruzados**: De 80+ a <5
- **Tiempo de tests**: Reducción del 40%
- **Cobertura de tests**: >90%
- **Performance**: Sin degradación
- **Tiempo de desarrollo**: Reducción del 30% para nuevas features

### Métricas Cualitativas:
- Facilidad para agregar nuevas funcionalidades
- Capacidad de testing independiente por dominio
- Claridad en la separación de responsabilidades
- Mantenibilidad del código

## 🚨 Gestión de Riesgos

### Riesgos Identificados:
1. **Performance del Event Bus**: Mitigado con tests de carga
2. **Complejidad de debugging**: Mitigado con correlation tracking
3. **Resistencia al cambio**: Mitigado con migración incremental
4. **Bugs en producción**: Mitigado con feature flags y rollback

### Estrategia de Rollback:
- Cada fase es reversible
- Feature flags para activar/desactivar eventos
- Mantener código legacy hasta validación completa
- Monitoring continuo durante migración

## 🎉 Beneficios Esperados

### Inmediatos (1-2 semanas):
- Mejor organización del código
- Tests más rápidos y focalizados
- Desarrollo paralelo más fácil

### Mediano Plazo (1-2 meses):
- Nuevas features más rápidas de implementar
- Bugs más fáciles de localizar y arreglar
- Onboarding de desarrolladores más simple

### Largo Plazo (3+ meses):
- Escalabilidad horizontal
- Microservicios más fáciles de extraer
- Arquitectura preparada para crecimiento

---

**Fecha de Inicio**: Semana del [FECHA]
**Duración Estimada**: 8 semanas
**Equipo**: [NOMBRES]
**Revisiones**: Semanales cada viernes