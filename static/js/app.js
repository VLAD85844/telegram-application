// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Конфигурация API
const STARS_API = "http://139.99.39.26:6555/api";

// Состояние приложения
let state = {
    products: [],
    cart: [],
    user: null,
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

// Инициализация приложения
async function initApp() {
    await loadUserData();
    await loadProducts();
    loadCart();
    updateUI();
    setupEventListeners();
}

// Загрузка данных пользователя
async function loadUserData() {
    try {
        const response = await fetch(`/api/user?user_id=${state.user.id}`);
        const data = await response.json();
        state.balance = data.balance;
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// Загрузка товаров
async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        state.products = await response.json();
        renderProducts(state.products);
    } catch (error) {
        console.error('Ошибка загрузки товаров:', error);
    }
}

// Отображение товаров
function renderProducts(products) {
    elements.productsContainer.innerHTML = '';
    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'col';
        productCard.innerHTML = `
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
        `;
        elements.productsContainer.appendChild(productCard);
    });
}

// Работа с корзиной
function loadCart() {
    const savedCart = localStorage.getItem('marketplace_cart');
    if (savedCart) state.cart = JSON.parse(savedCart);
}

function saveCart() {
    localStorage.setItem('marketplace_cart', JSON.stringify(state.cart));
}

function addToCart(productId) {
    const product = state.products.find(p => p.id === productId);
    if (!product) return;

    const existingItem = state.cart.find(item => item.product.id === productId);
    existingItem ? existingItem.quantity++ : state.cart.push({ product, quantity: 1 });

    saveCart();
    updateUI();
    showAlert(`"${product.name}" добавлен в корзину`);
}

// Удаление товара из корзины
function removeFromCart(productId) {
    state.cart = state.cart.filter(item => item.product.id !== productId);
    saveCart();
    updateUI();
}

// Обновление количества товара в корзине
function updateCartItemQuantity(productId, newQuantity) {
    const item = state.cart.find(item => item.product.id === productId);
    if (item) {
        item.quantity = Math.max(1, newQuantity); // Ограничиваем минимальное количество единицей
        saveCart();
        updateUI();
    }
}

// Платежная система
async function generateWallet() {
    try {
        const response = await fetch(`${STARS_API}/ton/generate`);
        return await response.json();
    } catch (error) {
        console.error('Ошибка генерации кошелька:', error);
        return null;
    }
}

async function getStarsPrice(quantity) {
    try {
        const response = await fetch(`${STARS_API}/stars/price/${quantity}`);
        return await response.json();
    } catch (error) {
        console.error('Ошибка получения цены:', error);
        return null;
    }
}

async function initPaymentFlow() {
    const neededStars = getCartTotal();

    try {
        const response = await fetch('/api/create-payment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                amount: neededStars,
                user_id: state.user?.id,
                cart: state.cart
            })
        });

        const paymentData = await response.json();

        if(paymentData.confirmation && paymentData.confirmation.confirmation_url) {
            // Открываем страницу оплаты
            window.open(paymentData.confirmation.confirmation_url, '_blank');

            // Стартуем проверку статуса
            const checkInterval = setInterval(async () => {
                const statusResponse = await fetch(`/api/check-payment/${paymentData.id}`);
                const status = await statusResponse.json();

                if(status === 'succeeded') {
                    clearInterval(checkInterval);
                    completeOrder();
                }
            }, 5000);
        }
    } catch (error) {
        showAlert('Ошибка оплаты: ' + error.message, 'error');
    }
}

function showPaymentDialog(data) {
    const dialogHTML = `
        <div class="payment-dialog">
            <h3>Оплата ${data.stars} ⭐</h3>
            <p>Сумма: ${data.tonAmount} TON ($${data.usdAmount})</p>
            <p>Кошелек для оплаты: <code>${data.wallet}</code></p>
            <button id="confirm-payment" class="btn btn-success">Я оплатил</button>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', dialogHTML);

    document.getElementById('confirm-payment').addEventListener('click', async () => {
        await checkPaymentStatus(data.wallet);
    });
}

async function checkPaymentStatus(wallet) {
    try {
        const response = await fetch(`${STARS_API}/stars/check-payment`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ address: wallet })
        });

        const result = await response.json();

        if (result.status === 'confirmed') {
            completeOrder();
        } else {
            showAlert('Платеж не обнаружен', 'warning');
        }
    } catch (error) {
        console.error('Ошибка проверки платежа:', error);
    }
}

function completeOrder() {
    state.cart = [];
    saveCart();
    updateUI();
    showAlert('Оплата успешно завершена!', 'success');
    tg.close();
}

// Обновление интерфейса
function getCartTotal() {
    return state.cart.reduce((total, item) => total + (item.product.price * item.quantity), 0);
}

function updateUI() {
    elements.starsCount.textContent = state.balance;
    renderCartItems();
    elements.cartCount.textContent = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    elements.cartTotal.textContent = `${getCartTotal()} ⭐`;
    elements.checkoutBtn.disabled = state.cart.length === 0;
}

function renderCartItems() {
    elements.cartItems.innerHTML = state.cart.length === 0
        ? '<p class="text-muted">Корзина пуста</p>'
        : state.cart.map(item => `
            <div class="cart-item" data-id="${item.product.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6>${item.product.name}</h6>
                        <small class="text-muted">${item.product.price} ⭐ × ${item.quantity} = ${item.product.price * item.quantity} ⭐</small>
                    </div>
                    <div class="d-flex align-items-center">
                        <div class="input-group input-group-sm me-2" style="width: 100px;">
                            <button class="btn btn-outline-secondary minus-btn">-</button>
                            <input type="number" class="form-control text-center quantity-input" value="${item.quantity}" min="1">
                            <button class="btn btn-outline-secondary plus-btn">+</button>
                        </div>
                        <button class="btn btn-sm btn-outline-danger remove-btn">✕</button>
                    </div>
                </div>
            </div>
        `).join('');

    // Добавляем обработчики для кнопок минус, плюс и удалить
    document.querySelectorAll('.minus-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const productId = parseInt(e.target.closest('.cart-item').dataset.id);
            updateCartItemQuantity(productId, parseInt(e.target.nextElementSibling.value) - 1);
        });
    });

    document.querySelectorAll('.plus-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const productId = parseInt(e.target.closest('.cart-item').dataset.id);
            updateCartItemQuantity(productId, parseInt(e.target.previousElementSibling.value) + 1);
        });
    });

    document.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const productId = parseInt(e.target.closest('.cart-item').dataset.id);
            removeFromCart(productId);
        });
    });

    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const productId = parseInt(e.target.closest('.cart-item').dataset.id);
            updateCartItemQuantity(productId, parseInt(e.target.value));
        });
    });
}

// Обработчики событий
function setupEventListeners() {
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('add-to-cart')) {
            const productId = parseInt(e.target.closest('.product-card').dataset.id);
            addToCart(productId);
        }

        if (e.target.id === 'checkout-btn') initPaymentFlow();
    });

    elements.openCartBtn.addEventListener('click', () => toggleCart(true));
    elements.closeCartBtn.addEventListener('click', () => toggleCart(false));

    elements.categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            elements.categoryButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const filtered = button.dataset.category === 'all'
                ? state.products
                : state.products.filter(p => p.category === button.dataset.category);
            renderProducts(filtered);
        });
    });

    tg.onEvent('viewportChanged', () => tg.isExpanded && tg.enableClosingConfirmation());
}

// Вспомогательные функции
function toggleCart(show) {
    elements.cartSidebar.classList.toggle('open', show);
    document.body.classList.toggle('no-scroll', show);
}

function showAlert(message, type = 'success') {
    alert(`[${type.toUpperCase()}] ${message}`);
}

// Запуск приложения
document.addEventListener('DOMContentLoaded', initApp);