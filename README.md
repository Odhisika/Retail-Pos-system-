# Django POS System

A comprehensive Point of Sale (POS) system built with Django, designed to streamline retail operations, inventory management, and sales reporting.

## 🚀 Features

*   **Point of Sale (POS)**: Intuitive interface for processing sales quickly and efficiently.
*   **Product Catalog**: Manage products, categories, and stock levels.
*   **Inventory Management**: Track stock movements and receive low-stock alerts.
*   **Customer Management**: Maintain customer profiles and purchase history.
*   **Wholesale Management**: Dedicated module for handling wholesale operations and invoices.
*   **Reporting & Analytics**: Generate detailed reports on sales, revenue, and performance.
*   **User Management**: Role-based access control for administrators and staff.

## 🛠️ Technology Stack

*   **Backend**: Django (Python)
*   **Database**: SQLite (Default) / PostgreSQL (Recommended for production)
*   **Frontend**: HTML, CSS, JavaScript (Bootstrap/Tailwind)

## 📦 Installation

Follow these steps to set up the project locally:

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/django-pos.git
    cd django-pos
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**
    *   **Windows**:
        ```bash
        venv\Scripts\activate
        ```
    *   **macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```

4.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If `requirements.txt` is missing, you can generate it from your current environment using `pip freeze > requirements.txt`)*

5.  **Apply database migrations**
    ```bash
    python manage.py migrate
    ```

6.  **Create a superuser**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the development server**
    ```bash
    python manage.py runserver
    ```

8.  **Access the application**
    Open your browser and navigate to `http://127.0.0.1:8000/`.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## 📄 License

This project is licensed under the MIT License.
