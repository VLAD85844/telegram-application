// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Состояние приложения
const state = {
    products: [],
    cart: [],
    balance: 0
};

// DOM элементы
const elements = {
    productsContainer: document.getElementById('products'),
    cartItems: document.getElementById('cart-items'),
    cartTotal: document.getElementById('cart-total'),
    cartCount: document.getElementById('cart-count'),
    starsCount: document.getElementById('stars-count'),
    openCartBtn: document.getElementById('open-cart'),
    closeCartBtn: document.getElementById('close-cart'),
    cartSidebar: document.getElementById('cart-sidebar'),
    checkoutBtn: document.getElementById('checkout-btn'),
    categoryButtons: document.querySelectorAll('[data-category]')
};

// Основные функции приложения
const App = {
    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.updateUI();
    },

    async loadData() {
        try {
            await Promise.all([this.loadProducts(), this.loadUserData()]);
            this.loadCart();
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
        }
    },

    async loadUserData() {
        const response = await fetch('/api/user');
        const data = await response.json();
        state.balance = data.balance;
    },

    async loadProducts() {
        const response = await fetch('/api/products');
        state.products = await response.json();
        this.renderProducts();
    },

    renderProducts() {
        elements.productsContainer.innerHTML = state.products
            .map(product => this.createProductCard(product))
            .join('');
    },

    createProductCard(product) {
        return `
            <div class="col">
                <div class="card product-card h-100" data-id="${product.id}">
                    <img src="${product.image}" class="card-img-top" alt="${product.name}">
                    <div class="card-body">
                        <h5 class="card-title">${product.name}</h5>
                        <p class="card-text">${product.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-primary">${product.price} ⭐</span>
                            <button class="btn btn-sm btn-outline-primary add-to-cart">Добавить</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // Работа с корзиной
    loadCart() {
        const savedCart = localStorage.getItem('marketplace_cart');
        if (savedCart) state.cart = JSON.parse(savedCart);
    },

    saveCart() {
        localStorage.setItem('marketplace_cart', JSON.stringify(state.cart));
    },

    handleCartAction(productId, action) {
        const product = state.products.find(p => p.id === productId);
        if (!product) return;

        switch(action) {
            case 'add':
                this.addToCart(product);
                break;
            case 'remove':
                this.removeFromCart(productId);
                break;
        }
    },

    addToCart(product) {
        const existingItem = state.cart.find(item => item.product.id === product.id);
        existingItem ? existingItem.quantity++ : state.cart.push({ product, quantity: 1 });
        this.updateCart();
        this.showAlert(`"${product.name}" добавлен в корзину`);
    },

    removeFromCart(productId) {
        state.cart = state.cart.filter(item => item.product.id !== productId);
        this.updateCart();
    },

    updateCartItemQuantity(productId, newQuantity) {
        const item = state.cart.find(item => item.product.id === productId);
        if (item) {
            item.quantity = Math.max(1, newQuantity);
            this.updateCart();
        }
    },

    updateCart() {
        this.saveCart();
        this.updateUI();
    },

    // Обновление интерфейса
    updateUI() {
        elements.starsCount.textContent = state.balance;
        elements.cartCount.textContent = this.getCartItemsCount();
        elements.cartTotal.textContent = `${this.getCartTotal()} ⭐`;
        elements.checkoutBtn.disabled = state.cart.length === 0;
        this.renderCartItems();
    },

    getCartTotal() {
        return state.cart.reduce((total, item) =>
            total + (item.product.price * item.quantity), 0);
    },

    getCartItemsCount() {
        return state.cart.reduce((sum, item) => sum + item.quantity, 0);
    },

    renderCartItems() {
        elements.cartItems.innerHTML = state.cart.length === 0
            ? '<p class="text-muted">Корзина пуста</p>'
            : state.cart.map(item => this.createCartItem(item)).join('');

        this.setupCartEventListeners();
    },

    createCartItem(item) {
        return `
            <div class="cart-item" data-id="${item.product.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6>${item.product.name}</h6>
                        <small class="text-muted">
                            ${item.product.price} ⭐ × ${item.quantity} = ${item.product.price * item.quantity} ⭐
                        </small>
                    </div>
                    <div class="d-flex align-items-center">
                        <div class="input-group input-group-sm me-2" style="width: 100px;">
                            <button class="btn btn-outline-secondary minus-btn">-</button>
                            <input type="number" 
                                   class="form-control text-center quantity-input" 
                                   value="${item.quantity}" 
                                   min="1">
                            <button class="btn btn-outline-secondary plus-btn">+</button>
                        </div>
                        <button class="btn btn-sm btn-outline-danger remove-btn">✕</button>
                    </div>
                </div>
            </div>
        `;
    },

    // Обработчики событий
    setupEventListeners() {
        document.addEventListener('click', this.handleDocumentClick.bind(this));
        elements.openCartBtn.addEventListener('click', () => this.toggleCart(true));
        elements.closeCartBtn.addEventListener('click', () => this.toggleCart(false));

        elements.categoryButtons.forEach(button => {
            button.addEventListener('click', () => this.handleCategoryFilter(button));
        });

        tg.onEvent('viewportChanged', () =>
            tg.isExpanded && tg.enableClosingConfirmation());
    },

    setupCartEventListeners() {
        elements.cartItems.addEventListener('click', (e) => {
            const cartItem = e.target.closest('.cart-item');
            if (!cartItem) return;

            const productId = parseInt(cartItem.dataset.id);

            if (e.target.classList.contains('minus-btn')) {
                this.updateCartItemQuantity(productId,
                    parseInt(e.target.nextElementSibling.value) - 1);
            }

            if (e.target.classList.contains('plus-btn')) {
                this.updateCartItemQuantity(productId,
                    parseInt(e.target.previousElementSibling.value) + 1);
            }

            if (e.target.classList.contains('remove-btn')) {
                this.removeFromCart(productId);
            }
        });

        elements.cartItems.addEventListener('change', (e) => {
            if (e.target.classList.contains('quantity-input')) {
                const cartItem = e.target.closest('.cart-item');
                this.updateCartItemQuantity(
                    parseInt(cartItem.dataset.id),
                    parseInt(e.target.value)
                );
            }
        });
    },

    handleDocumentClick(e) {
        if (e.target.classList.contains('add-to-cart')) {
            const productId = parseInt(e.target.closest('.product-card').dataset.id);
            this.handleCartAction(productId, 'add');
        }
    },

    handleCategoryFilter(button) {
        elements.categoryButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        const category = button.dataset.category;
        const filtered = category === 'all'
            ? state.products
            : state.products.filter(p => p.category === category);

        this.renderProducts(filtered);
    },

    // Вспомогательные функции
    toggleCart(show) {
        elements.cartSidebar.classList.toggle('open', show);
        document.body.classList.toggle('no-scroll', show);
    },

    showAlert(message, type = 'success') {
        const alertBox = document.createElement('div');
        alertBox.className = `alert alert-${type} mt-3`;
        alertBox.textContent = message;
        document.body.appendChild(alertBox);

        setTimeout(() => alertBox.remove(), 3000);
    }
};

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => App.init());