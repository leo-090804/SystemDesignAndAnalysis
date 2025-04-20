# Database Design

## Entity-Relationship Diagram (ERD)

```
+-------------+     +-------------+     +-------------+
|    User     |     |    Item     |     |   Event     |
+-------------+     +-------------+     +-------------+
| user_id PK  |     | item_id PK  |     | event_id PK |
| username    |     | title       |     | title       |
| password    |     | description |     | description |
| email       |     | category    |     | target      |
| full_name   |     | condition   |     | start_date  |
| role        |     | price       |     | end_date    |
| school_id   |     | status      |     | status      |
| created_at  |     | user_id FK  |     | organizer_id|
| last_login  |     | created_at  |     | created_at  |
+-------------+     | event_id FK |     +-------------+
       |             +-------------+            |
       |                    |                   |
       +--------------------+-------------------+
                            |
                    +----------------+
                    | Transaction    |
                    +----------------+
                    | txn_id PK      |
                    | seller_id FK   |
                    | buyer_id FK    |
                    | item_id FK     |
                    | event_id FK    |
                    | type           |
                    | amount         |
                    | status         |
                    | created_at     |
                    | completed_at   |
                    +----------------+
                            |
            +---------------+---------------+
            |                               |
    +-------------+                 +----------------+
    | Message     |                 | Review         |
    +-------------+                 +----------------+
    | msg_id PK   |                 | review_id PK   |
    | sender_id FK|                 | reviewer_id FK |
    | receiver_id |                 | reviewed_id FK |
    | txn_id FK   |                 | txn_id FK      |
    | content     |                 | rating         |
    | read_status |                 | comment        |
    | created_at  |                 | created_at     |
    +-------------+                 +----------------+
```

## Table Definitions

### User Table
```sql
CREATE TABLE User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('student', 'teacher', 'moderator', 'admin') NOT NULL,
    school_id VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    profile_picture VARCHAR(255)
);
```

### Item Table
```sql
CREATE TABLE Item (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    condition ENUM('new', 'like_new', 'good', 'fair', 'poor') NOT NULL,
    price DECIMAL(10, 2),
    status ENUM('draft', 'pending', 'approved', 'sold', 'exchanged', 'donated') NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_id INTEGER,
    image_paths TEXT,
    exchange_preferences TEXT,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (event_id) REFERENCES Event(event_id)
);
```

### Event Table
```sql
CREATE TABLE Event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    target DECIMAL(10, 2),
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    status ENUM('upcoming', 'active', 'completed', 'cancelled') NOT NULL,
    organizer_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    image_path VARCHAR(255),
    FOREIGN KEY (organizer_id) REFERENCES User(user_id)
);
```

### Transaction Table
```sql
CREATE TABLE Transaction (
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER,
    buyer_id INTEGER,
    item_id INTEGER NOT NULL,
    event_id INTEGER,
    type ENUM('sale', 'exchange', 'donation', 'event_contribution') NOT NULL,
    amount DECIMAL(10, 2),
    fee DECIMAL(10, 2) DEFAULT 0.00,
    status ENUM('pending', 'completed', 'cancelled') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (seller_id) REFERENCES User(user_id),
    FOREIGN KEY (buyer_id) REFERENCES User(user_id),
    FOREIGN KEY (item_id) REFERENCES Item(item_id),
    FOREIGN KEY (event_id) REFERENCES Event(event_id)
);
```

### Message Table
```sql
CREATE TABLE Message (
    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    txn_id INTEGER,
    content TEXT NOT NULL,
    read_status BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES User(user_id),
    FOREIGN KEY (receiver_id) REFERENCES User(user_id),
    FOREIGN KEY (txn_id) REFERENCES Transaction(txn_id)
);
```

### Review Table
```sql
CREATE TABLE Review (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER NOT NULL,
    reviewed_id INTEGER NOT NULL,
    txn_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reviewer_id) REFERENCES User(user_id),
    FOREIGN KEY (reviewed_id) REFERENCES User(user_id),
    FOREIGN KEY (txn_id) REFERENCES Transaction(txn_id)
);
```

### ItemImage Table
```sql
CREATE TABLE ItemImage (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    is_primary BOOLEAN DEFAULT 0,
    FOREIGN KEY (item_id) REFERENCES Item(item_id)
);
```

### Notification Table
```sql
CREATE TABLE Notification (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    reference_id INTEGER,
    read_status BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);
```