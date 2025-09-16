// POS JavaScript - Sistema de Ventas con Selección de Lotes
class POSSystem {
    constructor() {
        this.cart = [];
        this.products = [];
        this.currentOverrideItem = null;
        this.API_BASE = '/api/v1';
        
        this.init();
    }

    async init() {
        await this.loadProducts();
        this.setupEventListeners();
        this.renderProducts();
        this.updateCartDisplay();
    }

    async loadProducts() {
        try {
            const response = await fetch(`${this.API_BASE}/catalog/products`);
            const data = await response.json();
            this.products = data.results || data;
        } catch (error) {
            console.error('Error loading products:', error);
            this.showError('Error al cargar productos');
        }
    }

    setupEventListeners() {
        // Botón de checkout
        document.getElementById('checkout-btn').addEventListener('click', () => {
            this.processCheckout();
        });

        // Modal de override
        document.getElementById('cancel-override').addEventListener('click', () => {
            this.cancelOverride();
        });

        document.getElementById('confirm-override').addEventListener('click', () => {
            this.confirmOverride();
        });

        // Cerrar modal al hacer click fuera
        document.getElementById('override-modal').addEventListener('click', (e) => {
            if (e.target.id === 'override-modal') {
                this.cancelOverride();
            }
        });
    }

    renderProducts() {
        const grid = document.getElementById('products-grid');
        
        if (!this.products || this.products.length === 0) {
            grid.innerHTML = '<div class="loading">No hay productos disponibles</div>';
            return;
        }

        grid.innerHTML = this.products.map(product => `
            <div class="product-card" onclick="pos.addToCart(${product.id})">
                <div class="product-name">${product.name}</div>
                <div class="product-code">${product.code}</div>
                <div class="product-price">$${parseFloat(product.price).toFixed(2)}</div>
            </div>
        `).join('');
    }

    async addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) return;

        // Verificar si el producto ya está en el carrito
        const existingItem = this.cart.find(item => item.product.id === productId);
        if (existingItem) {
            existingItem.qty += 1;
            await this.updateLotOptions(existingItem);
        } else {
            // Crear nuevo item en el carrito
            const cartItem = {
                id: Date.now(), // ID único temporal
                product: product,
                qty: 1,
                lot_id: null,
                lot_override_reason: null,
                lotOptions: [],
                recommendedLotId: null
            };

            this.cart.push(cartItem);
            await this.updateLotOptions(cartItem);
        }

        this.updateCartDisplay();
    }

    async updateLotOptions(cartItem) {
        try {
            const response = await fetch(
                `${this.API_BASE}/stock/lots/options?product_id=${cartItem.product.id}&qty=${cartItem.qty}`
            );
            
            if (!response.ok) {
                throw new Error('Error al obtener opciones de lotes');
            }

            const data = await response.json();
            cartItem.lotOptions = data.options || [];
            cartItem.recommendedLotId = data.recommended_id;

            // Si no hay lote seleccionado, usar el recomendado
            if (!cartItem.lot_id && cartItem.recommendedLotId) {
                cartItem.lot_id = cartItem.recommendedLotId;
                cartItem.lot_override_reason = null; // No es override si es el recomendado
            }

        } catch (error) {
            console.error('Error loading lot options:', error);
            cartItem.lotOptions = [];
            cartItem.recommendedLotId = null;
        }
    }

    updateCartDisplay() {
        const cartContainer = document.getElementById('cart-items');
        const totalElement = document.getElementById('cart-total');
        const checkoutBtn = document.getElementById('checkout-btn');

        if (this.cart.length === 0) {
            cartContainer.innerHTML = '<div class="loading">El carrito está vacío</div>';
            totalElement.textContent = '$0.00';
            checkoutBtn.disabled = true;
            return;
        }

        // Renderizar items del carrito
        cartContainer.innerHTML = this.cart.map(item => this.renderCartItem(item)).join('');

        // Calcular total
        const total = this.cart.reduce((sum, item) => {
            return sum + (parseFloat(item.product.price) * item.qty);
        }, 0);

        totalElement.textContent = `$${total.toFixed(2)}`;

        // Habilitar checkout si todos los items tienen lote seleccionado
        const allItemsHaveLots = this.cart.every(item => item.lot_id);
        checkoutBtn.disabled = !allItemsHaveLots;
    }

    renderCartItem(item) {
        const selectedLot = item.lotOptions.find(lot => lot.id === item.lot_id);
        const isRecommended = item.lot_id === item.recommendedLotId;
        const isOverride = item.lot_id && !isRecommended;

        return `
            <div class="cart-item">
                <div class="cart-item-header">
                    <div class="cart-item-info">
                        <div class="cart-item-name">${item.product.name}</div>
                        <div class="cart-item-code">${item.product.code}</div>
                    </div>
                    <button class="cart-item-remove" onclick="pos.removeFromCart(${item.id})">
                        ✕
                    </button>
                </div>

                <div class="cart-item-controls">
                    <div class="form-group">
                        <label class="form-label">Cantidad</label>
                        <input 
                            type="number" 
                            class="form-input" 
                            value="${item.qty}" 
                            min="1" 
                            step="0.001"
                            onchange="pos.updateQuantity(${item.id}, this.value)"
                        >
                    </div>

                    <div class="form-group">
                        <label class="form-label">Lote</label>
                        <select 
                            class="form-select" 
                            onchange="pos.changeLot(${item.id}, this.value)"
                            ${item.lotOptions.length === 0 ? 'disabled' : ''}
                        >
                            ${item.lotOptions.length === 0 
                                ? '<option>Sin lotes disponibles</option>'
                                : item.lotOptions.map(lot => `
                                    <option value="${lot.id}" ${lot.id === item.lot_id ? 'selected' : ''}>
                                        ${lot.lot_code} - ${lot.qty_on_hand} unid.
                                        ${lot.id === item.recommendedLotId ? ' (Recomendado)' : ''}
                                    </option>
                                `).join('')
                            }
                        </select>
                    </div>
                </div>

                ${selectedLot ? `
                    <div class="lot-info ${isRecommended ? 'lot-recommended' : (isOverride ? 'lot-override' : '')}">
                        <strong>${selectedLot.lot_code}</strong> - 
                        Vence: ${new Date(selectedLot.expiry_date).toLocaleDateString()} - 
                        Stock: ${selectedLot.qty_on_hand}
                        ${isRecommended ? ' ✓ Recomendado FEFO' : ''}
                        ${isOverride ? ' ⚠ Override' : ''}
                    </div>
                ` : ''}

                ${isOverride && item.lot_override_reason ? `
                    <div class="alert alert-warning">
                        <strong>Motivo del override:</strong> ${item.lot_override_reason}
                    </div>
                ` : ''}
            </div>
        `;
    }

    async updateQuantity(itemId, newQty) {
        const item = this.cart.find(i => i.id === itemId);
        if (!item) return;

        const qty = parseFloat(newQty);
        if (qty <= 0) {
            this.removeFromCart(itemId);
            return;
        }

        item.qty = qty;
        await this.updateLotOptions(item);
        this.updateCartDisplay();
    }

    async changeLot(itemId, newLotId) {
        const item = this.cart.find(i => i.id === itemId);
        if (!item) return;

        const lotId = parseInt(newLotId);
        const isRecommended = lotId === item.recommendedLotId;

        if (isRecommended) {
            // Si es el lote recomendado, cambiar directamente
            item.lot_id = lotId;
            item.lot_override_reason = null;
            this.updateCartDisplay();
        } else {
            // Si no es el recomendado, mostrar modal de override
            this.currentOverrideItem = item;
            this.showOverrideModal(item, lotId);
        }
    }

    showOverrideModal(item, newLotId) {
        const modal = document.getElementById('override-modal');
        const reasonInput = document.getElementById('override-reason');
        const pinInput = document.getElementById('override-pin');
        const pinGroup = document.getElementById('pin-group');
        const alertsContainer = document.getElementById('override-alerts');

        // Limpiar campos
        reasonInput.value = '';
        pinInput.value = '';
        alertsContainer.innerHTML = '';

        // Mostrar/ocultar PIN según configuración
        // Por ahora siempre mostrar PIN para overrides
        pinGroup.style.display = 'block';

        // Guardar el nuevo lote ID temporalmente
        this.currentOverrideItem.tempLotId = newLotId;

        modal.classList.add('show');
        reasonInput.focus();
    }

    cancelOverride() {
        const modal = document.getElementById('override-modal');
        modal.classList.remove('show');

        // Revertir la selección al lote actual
        if (this.currentOverrideItem) {
            this.updateCartDisplay();
            this.currentOverrideItem = null;
        }
    }

    confirmOverride() {
        const reasonInput = document.getElementById('override-reason');
        const pinInput = document.getElementById('override-pin');
        const alertsContainer = document.getElementById('override-alerts');

        // Validaciones
        const reason = reasonInput.value.trim();
        const pin = pinInput.value.trim();

        alertsContainer.innerHTML = '';

        if (!reason) {
            alertsContainer.innerHTML = `
                <div class="alert alert-danger">
                    El motivo del override es obligatorio
                </div>
            `;
            reasonInput.focus();
            return;
        }

        if (!pin) {
            alertsContainer.innerHTML = `
                <div class="alert alert-danger">
                    El PIN de autorización es obligatorio
                </div>
            `;
            pinInput.focus();
            return;
        }

        // Aplicar el override
        if (this.currentOverrideItem) {
            this.currentOverrideItem.lot_id = this.currentOverrideItem.tempLotId;
            this.currentOverrideItem.lot_override_reason = reason;
            this.currentOverrideItem.override_pin = pin;
            delete this.currentOverrideItem.tempLotId;
        }

        // Cerrar modal
        const modal = document.getElementById('override-modal');
        modal.classList.remove('show');
        this.currentOverrideItem = null;

        this.updateCartDisplay();
    }

    removeFromCart(itemId) {
        this.cart = this.cart.filter(item => item.id !== itemId);
        this.updateCartDisplay();
    }

    async processCheckout() {
        // Validar que todos los items tengan lote
        const itemsWithoutLot = this.cart.filter(item => !item.lot_id);
        if (itemsWithoutLot.length > 0) {
            this.showError('Todos los productos deben tener un lote seleccionado');
            return;
        }

        // Validar que los overrides tengan motivo
        const overridesWithoutReason = this.cart.filter(item => 
            item.lot_id !== item.recommendedLotId && !item.lot_override_reason
        );
        if (overridesWithoutReason.length > 0) {
            this.showError('Los overrides de lote deben tener un motivo');
            return;
        }

        try {
            const checkoutBtn = document.getElementById('checkout-btn');
            checkoutBtn.disabled = true;
            checkoutBtn.textContent = 'Procesando...';

            // Preparar payload para la API
            const payload = {
                items: this.cart.map(item => ({
                    product_id: item.product.id,
                    qty: item.qty.toString(),
                    lot_id: item.lot_id,
                    lot_override_reason: item.lot_override_reason || undefined
                })),
                override_pin: this.cart.find(item => item.override_pin)?.override_pin || undefined
            };

            const response = await fetch(`${this.API_BASE}/pos/sale`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Error en la venta');
            }

            const result = await response.json();
            
            // Venta exitosa
            this.showSuccess(`Venta procesada exitosamente. ID: ${result.sale_id}`);
            this.clearCart();

        } catch (error) {
            console.error('Checkout error:', error);
            this.showError(error.message || 'Error al procesar la venta');
        } finally {
            const checkoutBtn = document.getElementById('checkout-btn');
            checkoutBtn.disabled = false;
            checkoutBtn.textContent = 'Procesar Venta';
        }
    }

    clearCart() {
        this.cart = [];
        this.updateCartDisplay();
    }

    showError(message) {
        // Implementar notificación de error
        alert(`Error: ${message}`);
    }

    showSuccess(message) {
        // Implementar notificación de éxito
        alert(`Éxito: ${message}`);
    }
}

// Inicializar el sistema POS
const pos = new POSSystem();