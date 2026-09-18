import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Mini Mart",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background: #000;
            color: #fff;
        }

        [data-testid="stHeader"] {
            background: #000;
        }

        .main-title {
            color: #2196F3;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0;
        }

        .welcome {
            color: #ddd;
            font-size: 1rem;
            margin-bottom: 1rem;
        }

        .product-card {
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 12px;
            padding: 18px;
            min-height: 250px;
            margin-bottom: 12px;
        }

        .product-image {
            height: 100px;
            border-radius: 8px;
            background: #292929;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5rem;
            margin-bottom: 12px;
        }

        .product-name {
            font-size: 1.05rem;
            font-weight: 700;
            min-height: 48px;
        }

        .product-price {
            color: #2196F3;
            font-size: 1.25rem;
            font-weight: 700;
            margin: 6px 0 12px;
        }

        .category-title {
            color: #2196F3;
            border-bottom: 2px solid #333;
            padding-bottom: 8px;
            margin-top: 25px;
        }

        .cart-item {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }

        .cart-total {
            border-top: 2px solid #333;
            padding-top: 15px;
            font-size: 1.35rem;
            font-weight: 700;
        }

        .order-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
        }

        .order-number {
            color: #2196F3;
            font-size: 1.2rem;
            font-weight: 700;
        }

        div.stButton > button {
            border-radius: 7px;
        }

        section[data-testid="stSidebar"] {
            background: #111;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FIREBASE CONFIGURATION
# ============================================================

# Your new Firebase Realtime Database
DEFAULT_FIREBASE_DATABASE_URL = (
    "https://for-minimart-streamlit-ver-default-rtdb."
    "asia-southeast1.firebasedatabase.app"
)

try:
    FIREBASE_DATABASE_URL = st.secrets["firebase"]["database_url"]
except Exception:
    FIREBASE_DATABASE_URL = DEFAULT_FIREBASE_DATABASE_URL


# FormSubmit email
try:
    FORMSUBMIT_EMAIL = st.secrets["formsubmit"]["email"]
except Exception:
    FORMSUBMIT_EMAIL = "clive.lin.dino@gmail.com"


# ============================================================
# FIRESTORE INITIALIZATION
# ============================================================

@st.cache_resource
def initialize_firestore():
    """
    Initializes Firebase Admin SDK once and returns
    the Firestore client.
    """

    if not firebase_admin._apps:
        try:
            firebase_config = dict(st.secrets["firebase_service_account"])

            cred = credentials.Certificate(firebase_config)

            firebase_admin.initialize_app(cred)

        except Exception as exc:
            raise RuntimeError(
                "Firebase Admin SDK could not be initialized. "
                "Check your [firebase_service_account] secrets."
            ) from exc

    return firestore.client()


try:
    FIRESTORE_DB = initialize_firestore()
    FIRESTORE_ERROR = None
except Exception as exc:
    FIRESTORE_DB = None
    FIRESTORE_ERROR = str(exc)


# ============================================================
# PRODUCTS
# ============================================================

PRODUCTS: Dict[str, List[Dict[str, Any]]] = {
    "cookies": [
        {"id": "cookies-1", "name": "Lays Chips ~50g", "price": 40},
        {"id": "cookies-2", "name": "Doritos ~50g", "price": 40},
        {"id": "cookies-3", "name": "Pringles ~50g", "price": 40},
    ],
    "snacks": [
        {"id": "snacks-1", "name": "Airwaves", "price": 50},
        {"id": "snacks-2", "name": "Hersheys", "price": 50},
    ],
    "drinks": [
        {"id": "drinks-1", "name": "Coke ~350ml", "price": 50},
        {"id": "drinks-2", "name": "Sprite ~350ml", "price": 50},
        {"id": "drinks-3", "name": "Orange Juice ~200ml", "price": 50},
        {"id": "drinks-4", "name": "Pepsi ~350ml", "price": 50},
    ],
    "ramen": [
        {"id": "ramen-1", "name": "Cup Noodles", "price": 60},
        {"id": "ramen-2", "name": "Shin Ramen", "price": 70},
    ],
    "donuts": [
        {"id": "donuts-1", "name": "Glazed Donut", "price": 50},
        {"id": "donuts-2", "name": "Chocolate Donut", "price": 50},
    ],
    "giftcards": [
        {"id": "giftcard-1", "name": "Minecraft Gift Card", "price": 800},
        {"id": "giftcard-2", "name": "Google Play Gift Card", "price": 500},
    ],
}


CATEGORY_LABELS = {
    "cookies": "Cookies",
    "snacks": "Snacks",
    "drinks": "Drinks",
    "ramen": "Instant Ramen",
    "donuts": "Donuts",
    "giftcards": "Gift Cards",
}


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "logged_in": False,
    "username": "",
    "cart": [],
    "quantities": {},
    "page": "shop",
    "auth_mode": "login",
    "checkout_open": False,
    "history_open": False,
    "thank_you_order": None,
    "checkout_order_number": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# FIREBASE REALTIME DATABASE HELPERS
# ============================================================

def firebase_url(path: str) -> str:
    base = FIREBASE_DATABASE_URL.rstrip("/")
    path = path.strip("/")

    return f"{base}/{path}.json"


def firebase_get(path: str) -> Any:
    response = requests.get(
        firebase_url(path),
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def firebase_put(path: str, data: Any) -> Any:
    response = requests.put(
        firebase_url(path),
        json=data,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# PRODUCT HELPERS
# ============================================================

def get_all_products() -> Dict[str, Dict[str, Any]]:
    return {
        product["id"]: product
        for category in PRODUCTS.values()
        for product in category
    }


def find_product(product_id: str) -> Optional[Dict[str, Any]]:
    return get_all_products().get(product_id)


# ============================================================
# CART HELPERS
# ============================================================

def cart_total() -> int:
    return sum(
        item["price"] * item["quantity"]
        for item in st.session_state.cart
    )


def cart_count() -> int:
    return sum(
        item["quantity"]
        for item in st.session_state.cart
    )


def add_to_cart(product_id: str) -> None:
    product = find_product(product_id)

    if not product:
        return

    quantity = max(
        1,
        int(
            st.session_state.quantities.get(
                product_id,
                1,
            )
        ),
    )

    # Keep original behavior:
    # every Add to Cart click creates a separate cart entry.
    st.session_state.cart.append(
        {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
        }
    )

    st.session_state.quantities[product_id] = 1


# ============================================================
# AUTH MESSAGE HELPERS
# ============================================================

def reset_auth_message() -> None:
    st.session_state.pop("auth_message", None)


def set_auth_message(
    message: str,
    kind: str = "error",
) -> None:
    st.session_state.auth_message = {
        "message": message,
        "kind": kind,
    }


# ============================================================
# AUTH
# ============================================================

def register_user(
    username: str,
    password: str,
    confirm: str,
) -> bool:

    username = username.strip()

    if not username:
        set_auth_message(
            "Please enter a username."
        )
        return False

    if password != confirm:
        set_auth_message(
            "Passwords do not match."
        )
        return False

    if len(password) < 4:
        set_auth_message(
            "Password must be at least 4 characters."
        )
        return False

    try:
        existing = firebase_get(
            f"users/{username}"
        )

        if existing is not None:
            set_auth_message(
                "Username already exists."
            )
            return False

        # NOTE:
        # This keeps your existing database structure.
        # For a real production application, Firebase Authentication
        # should be used instead of storing passwords directly.
        firebase_put(
            f"users/{username}",
            {
                "password": password,
                "createdAt": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
        )

        set_auth_message(
            "Account created successfully! "
            "You can now login.",
            "success",
        )

        return True

    except requests.RequestException as exc:
        set_auth_message(
            f"Registration failed: {exc}"
        )
        return False


def login_user(
    username: str,
    password: str,
) -> bool:

    username = username.strip()

    try:
        user = firebase_get(
            f"users/{username}"
        )

        if user is None:
            set_auth_message(
                "Username not found."
            )
            return False

        if user.get("password") != password:
            set_auth_message(
                "Incorrect password."
            )
            return False

        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.page = "shop"
        st.session_state.cart = []

        reset_auth_message()

        return True

    except requests.RequestException as exc:
        set_auth_message(
            f"Login failed: {exc}"
        )
        return False


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.cart = []
    st.session_state.page = "shop"
    st.session_state.checkout_open = False
    st.session_state.history_open = False
    st.session_state.thank_you_order = None
    st.session_state.checkout_order_number = None

    st.rerun()


# ============================================================
# FIRESTORE ORDERS
# ============================================================

def save_order(order: Dict[str, Any]) -> None:
    """
    Saves an order to Firestore.

    Firestore will automatically create the 'orders'
    collection when the first order is saved.
    """

    if FIRESTORE_DB is None:
        raise RuntimeError(
            "Firestore is not initialized. "
            "Check your Firebase service account configuration."
        )

    FIRESTORE_DB.collection("orders").add(order)


def load_order_history(
    username: str,
) -> List[Dict[str, Any]]:

    if FIRESTORE_DB is None:
        raise RuntimeError(
            "Firestore is not initialized."
        )

    orders: List[Dict[str, Any]] = []

    documents = (
        FIRESTORE_DB
        .collection("orders")
        .where(
            filter=firestore.FieldFilter(
                "username",
                "==",
                username,
            )
        )
        .stream()
    )

    for document in documents:
        order = document.to_dict()

        if isinstance(order, dict):
            order["id"] = document.id
            orders.append(order)

    orders.sort(
        key=lambda x: x.get(
            "timestamp",
            0,
        ) or 0,
        reverse=True,
    )

    return orders


# ============================================================
# EMAIL
# ============================================================

def send_order_email(
    order_number: int,
    username: str,
    name: str,
    email: str,
    phone: str,
    items: str,
    total: int,
    notes: str,
) -> bool:
    """Send an order email through FormSubmit."""

    formsubmit_token = "c8e3214f719936ffedbe8bb92367f2ab"

    form_data = {
        "order_number": str(order_number),
        "username": username,
        "name": name,
        "email": email,
        "phone": phone,
        "items": items,
        "total": f"${total}",
        "notes": notes,

        "_subject": f"Mini Mart Order #{order_number}",
        "_template": "table",
    }

    try:
        response = requests.post(
            f"https://formsubmit.co/ajax/{formsubmit_token}",
            data=form_data,
            headers={
                "Accept": "application/json",
            },
            timeout=20,
        )

        try:
            result = response.json()
        except ValueError:
            st.error(
                f"FormSubmit returned an unexpected response "
                f"(HTTP {response.status_code})."
            )
            st.code(response.text[:2000])
            return False

        if response.status_code >= 400:
            st.error(f"FormSubmit failed: HTTP {response.status_code}")
            st.code(str(result))
            return False

        if result.get("success") is True:
            return True

        st.error("FormSubmit did not confirm the submission.")
        st.code(str(result))
        return False

    except requests.RequestException as exc:
        st.error(f"Could not connect to FormSubmit: {exc}")
        return False

# ============================================================
# CHECKOUT PROCESS
# ============================================================

def complete_checkout(
    name: str,
    email: str,
    phone: str,
    notes: str,
) -> None:

    if not st.session_state.cart:
        st.error(
            "Your cart is empty."
        )
        return

    order_number = (
        st.session_state.checkout_order_number
    )

    if order_number is None:
        order_number = random.randint(
            100000,
            999999,
        )

    total = cart_total()

    items = "\n".join(
        f"{item['name']} x{item['quantity']}"
        for item in st.session_state.cart
    )

    now = datetime.now(timezone.utc)

    order = {
        "username": st.session_state.username,
        "orderNumber": order_number,
        "items": items,
        "total": total,
        "date": now.isoformat(),
        "timestamp": int(
            now.timestamp() * 1000
        ),
    }

    try:
        # ----------------------------------------------------
        # SAVE TO FIRESTORE
        # ----------------------------------------------------
        save_order(order)

        # ----------------------------------------------------
        # SEND EMAIL
        # ----------------------------------------------------
        send_order_email(
            order_number,
            st.session_state.username,
            name,
            email,
            phone,
            items,
            total,
            notes,
        )

        # ----------------------------------------------------
        # CLEAR CART
        # ----------------------------------------------------
        st.session_state.cart = []

        st.session_state.checkout_open = False

        st.session_state.thank_you_order = (
            order_number
        )

        st.session_state.checkout_order_number = None

        st.rerun()

    except Exception as exc:
        st.error(
            f"There was an error placing your order: {exc}"
        )


# ============================================================
# AUTH PAGE
# ============================================================

def render_auth_page() -> None:

    st.markdown(
        "<div style='height:8vh'></div>",
        unsafe_allow_html=True,
    )

    left, center, right = st.columns(
        [1, 1.2, 1]
    )

    with center:

        st.markdown(
            """
            <div style="
                background:white;
                color:#333;
                border-radius:20px;
                padding:30px 35px;
                text-align:center
            ">
                <h1 style="
                    color:#2575fc;
                    margin-bottom:5px
                ">
                    🏪 Mini Mart
                </h1>

                <p style="color:#666">
                    Login or create an account
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        login_tab, register_tab = st.tabs(
            ["Login", "Register"]
        )

        # ----------------------------------------------------
        # LOGIN
        # ----------------------------------------------------

        with login_tab:

            with st.form("login_form"):

                username = st.text_input(
                    "Username",
                    key="login_username",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password",
                )

                submitted = st.form_submit_button(
                    "Login",
                    use_container_width=True,
                    type="primary",
                )

            if submitted:

                if login_user(
                    username,
                    password,
                ):
                    st.rerun()

        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        with register_tab:

            with st.form("register_form"):

                username = st.text_input(
                    "Username",
                    key="register_username",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="register_password",
                )

                confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    key="register_confirm",
                )

                submitted = st.form_submit_button(
                    "Create Account",
                    use_container_width=True,
                    type="primary",
                )

            if submitted:

                if register_user(
                    username,
                    password,
                    confirm,
                ):
                    st.rerun()

        # ----------------------------------------------------
        # AUTH MESSAGE
        # ----------------------------------------------------

        message = st.session_state.get(
            "auth_message"
        )

        if message:

            if message["kind"] == "success":
                st.success(
                    message["message"]
                )
            else:
                st.error(
                    message["message"]
                )


# ============================================================
# PRODUCT CARD
# ============================================================

def render_product(
    category: str,
    product: Dict[str, Any],
) -> None:

    product_id = product["id"]

    quantity = int(
        st.session_state.quantities.get(
            product_id,
            1,
        )
    )

    st.markdown(
        f"""
        <div class="product-card">

            <div class="product-image">
                📦
            </div>

            <div class="product-name">
                {product['name']}
            </div>

            <div class="product-price">
                ${product['price']}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    minus, qty, plus = st.columns(
        [1, 1.2, 1]
    )

    with minus:

        if st.button(
            "−",
            key=f"minus_{product_id}",
            use_container_width=True,
        ):

            st.session_state.quantities[
                product_id
            ] = max(
                1,
                quantity - 1,
            )

            st.rerun()

    with qty:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding:7px
            ">
                Quantity:
                <b>{quantity}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with plus:

        if st.button(
            "+",
            key=f"plus_{product_id}",
            use_container_width=True,
        ):

            st.session_state.quantities[
                product_id
            ] = quantity + 1

            st.rerun()

    if st.button(
        "Add to Cart",
        key=f"add_{product_id}",
        use_container_width=True,
        type="primary",
    ):

        add_to_cart(product_id)

        st.toast(
            f"Added {product['name']} x{quantity}"
        )

        st.rerun()


# ============================================================
# SHOP
# ============================================================

def render_shop() -> None:

    header_left, header_mid, header_right = st.columns(
        [2.5, 2, 2.5]
    )

    with header_left:

        st.markdown(
            '<div class="main-title">🏪 Mini Mart</div>',
            unsafe_allow_html=True,
        )

    with header_mid:

        st.markdown(
            f"""
            <div class="welcome">
                Welcome,
                <b>{st.session_state.username}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_right:

        b1, b2, b3 = st.columns(3)

        with b1:

            if st.button(
                f"🛒 Cart ({cart_count()})",
                use_container_width=True,
            ):

                st.session_state.page = "cart"
                st.rerun()

        with b2:

            if st.button(
                "📜 History",
                use_container_width=True,
            ):

                st.session_state.page = "history"
                st.rerun()

        with b3:

            if st.button(
                "Logout",
                use_container_width=True,
            ):

                logout()

    st.divider()

    # --------------------------------------------------------
    # CATEGORY NAVIGATION
    # --------------------------------------------------------

    nav_cols = st.columns(
        len(CATEGORY_LABELS)
    )

    for column, (
        category,
        label,
    ) in zip(
        nav_cols,
        CATEGORY_LABELS.items(),
    ):

        with column:

            if st.button(
                label,
                key=f"nav_{category}",
                use_container_width=True,
            ):

                st.session_state.page = category
                st.rerun()

    # --------------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------------

    if st.session_state.page in CATEGORY_LABELS:

        categories_to_render = [
            st.session_state.page
        ]

        if st.button(
            "← Show All Products"
        ):

            st.session_state.page = "shop"
            st.rerun()

    else:

        categories_to_render = list(
            PRODUCTS.keys()
        )

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    for category in categories_to_render:

        st.markdown(
            f"""
            <h2 class="category-title">
                {CATEGORY_LABELS[category]}
            </h2>
            """,
            unsafe_allow_html=True,
        )

        products = PRODUCTS[category]

        columns = st.columns(
            min(
                4,
                len(products),
            )
        )

        for index, product in enumerate(
            products
        ):

            with columns[
                index % len(columns)
            ]:

                render_product(
                    category,
                    product,
                )


# ============================================================
# CART
# ============================================================

def render_cart() -> None:

    st.markdown(
        '<div class="main-title">🛒 Your Cart</div>',
        unsafe_allow_html=True,
    )

    if st.button("← Back to Shop"):

        st.session_state.page = "shop"
        st.rerun()

    st.divider()

    if not st.session_state.cart:

        st.info(
            "Your cart is empty."
        )

        return

    # --------------------------------------------------------
    # CART ITEMS
    # --------------------------------------------------------

    for index, item in enumerate(
        st.session_state.cart
    ):

        left, middle, right = st.columns(
            [4, 2, 1]
        )

        with left:

            st.markdown(
                f"""
                **{item['name']}**

                Quantity: {item['quantity']}
                """
            )

        with middle:

            st.markdown(
                f"### ${item['price'] * item['quantity']}"
            )

        with right:

            if st.button(
                "Remove",
                key=f"remove_{index}",
            ):

                st.session_state.cart.pop(
                    index
                )

                st.rerun()

        st.divider()

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="cart-total">
            Total: ${cart_total()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # CHECKOUT
    # --------------------------------------------------------

    if st.button(
        "Checkout",
        type="primary",
        use_container_width=True,
    ):

        st.session_state.checkout_order_number = (
            random.randint(
                100000,
                999999,
            )
        )

        st.session_state.checkout_open = True

        st.rerun()

    if st.session_state.checkout_open:

        render_checkout()


# ============================================================
# CHECKOUT
# ============================================================

def render_checkout() -> None:

    st.markdown("---")

    st.subheader("Checkout")

    st.info(
        f"Order Number: "
        f"#{st.session_state.checkout_order_number}"
    )

    with st.form("checkout_form"):

        name = st.text_input(
            "Customer Name"
        )

        email = st.text_input(
            "Customer Email"
        )

        phone = st.text_input(
            "Phone"
        )

        notes = st.text_area(
            "Notes"
        )

        col1, col2 = st.columns(2)

        with col1:

            submit = st.form_submit_button(
                "Place Order",
                type="primary",
                use_container_width=True,
            )

        with col2:

            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True,
            )

    if cancel:

        st.session_state.checkout_open = False

        st.rerun()

    if submit:

        if (
            not name.strip()
            or not email.strip()
            or not phone.strip()
        ):

            st.warning(
                "Please fill in your name, "
                "email, and phone number."
            )

        else:

            complete_checkout(
                name,
                email,
                phone,
                notes,
            )


# ============================================================
# THANK YOU
# ============================================================

def render_thank_you() -> None:

    order_number = (
        st.session_state.thank_you_order
    )

    st.success(
        "Order placed successfully!"
    )

    st.markdown(
        f"""
        <div style="
            text-align:center
        ">

            <h2>
                Thank you for your order!
            </h2>

            <p>
                Your order number is:
            </p>

            <div class="order-number">
                #{order_number}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Continue Shopping",
        type="primary",
        use_container_width=True,
    ):

        st.session_state.thank_you_order = None

        st.session_state.page = "shop"

        st.rerun()


# ============================================================
# ORDER HISTORY
# ============================================================

def render_history() -> None:

    st.markdown(
        '<div class="main-title">📜 Order History</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "← Back to Shop"
    ):

        st.session_state.page = "shop"
        st.rerun()

    st.divider()

    try:

        orders = load_order_history(
            st.session_state.username
        )

    except Exception as exc:

        st.error(
            f"Could not load order history: {exc}"
        )

        return

    if not orders:

        st.info(
            "No orders yet."
        )

        return

    # --------------------------------------------------------
    # DISPLAY ORDERS
    # --------------------------------------------------------

    for order in orders:

        date_text = order.get(
            "date",
            "Unknown date",
        )

        try:

            date_text = (
                datetime.fromisoformat(
                    date_text.replace(
                        "Z",
                        "+00:00",
                    )
                )
                .astimezone()
                .strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        except Exception:
            pass

        st.markdown(
            f"""
            <div class="order-card">

                <div class="order-number">
                    Order #
                    {order.get(
                        'orderNumber',
                        'N/A'
                    )}
                </div>

                <p>
                    <b>Total:</b>
                    ${order.get(
                        'total',
                        0
                    )}
                </p>

                <p>
                    <b>Date:</b>
                    {date_text}
                </p>

                <p>
                    <b>Items:</b>
                </p>

                <p style="
                    white-space:pre-line;
                    color:#aaa
                ">
                    {order.get(
                        'items',
                        ''
                    )}
                </p>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# FIREBASE STATUS
# ============================================================

# This is intentionally shown only when the user is logged in.
# It helps diagnose configuration problems without exposing
# credentials.

if st.session_state.logged_in and FIRESTORE_ERROR:

    st.warning(
        "Firestore is not currently connected. "
        "Order history and checkout may not work until "
        "the Firebase service account is configured."
    )


# ============================================================
# MAIN APP
# ============================================================

if not st.session_state.logged_in:

    render_auth_page()

else:

    if st.session_state.thank_you_order is not None:

        render_thank_you()

    elif st.session_state.page == "cart":

        render_cart()

    elif st.session_state.page == "history":

        render_history()

    else:

        render_shop()
