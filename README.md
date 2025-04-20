# School Item Exchange/Donation Application

A PyQt5-based desktop application for school communities to buy, sell, exchange, and donate school items, as well as organize and participate in fundraising events.

## Features

- **User Management**
  - Registration and authentication
  - Different roles: Student, Teacher, Moderator, Admin
  - User profile and activity tracking

- **Item Management**
  - Create, view, edit, and delete items
  - Upload item images
  - Categorization and filtering
  - Item approval workflow

- **Transaction Types**
  - Sale: Direct purchase of items
  - Exchange: Trading items between users
  - Donation: Giving away items
  - Event contribution: Items donated to fundraising events

- **Event Management**
  - Create and manage fundraising/donation events
  - Set targets and track progress
  - Timeline and event status tracking
  - User contributions to events

- **Communication Features**
  - In-app notifications
  - Transaction messaging

## Requirements

- Python 3.8+
- PyQt5 (GUI framework)
- SQLite (database)
- Additional dependencies in requirements.txt

## Installation

1. Clone the repository or download the source code:

```bash
git clone <repository-url>
cd school-exchange-app
```

2. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

## Running the Application

To start the application, run:

```bash
python src/app.py
```

## Default Credentials

The application automatically creates a default admin user on first run:

- Username: admin
- Password: admin123
- Email: admin@school.edu

## Database Structure

The application uses SQLite for data storage with the following main tables:

- User: Store user accounts and profiles
- Item: Store item listings and details
- Event: Store fundraising/donation events
- Transaction: Store all types of transactions
- Message: Store user-to-user messages
- Review: Store user reviews and ratings
- Notification: Store user notifications

## Application Structure

The application follows the MVC pattern:

- **Models**: Data models and database operations
  - `src/models/user.py`: User account management
  - `src/models/item.py`: Item listing and management
  - `src/models/transaction.py`: Transaction processing
  - `src/models/event.py`: Event management

- **Views**: UI components using PyQt5
  - `src/views/login_view.py`: Login and registration
  - `src/views/main_window.py`: Main application window
  - `src/views/dashboard_view.py`: User dashboard
  - `src/views/items_view.py`: Item browsing and management
  - `src/views/events_view.py`: Event browsing and management
  - `src/views/transactions_view.py`: Transaction history and actions

- **Database**: Data storage and schema
  - `src/database/schema.py`: Database schema and initialization

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

This project was created as part of the System Design and Analysis course.