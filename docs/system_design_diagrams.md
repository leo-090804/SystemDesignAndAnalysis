# System Design Diagrams

## Context Diagram

```
                     +-------------------+
                     |                   |
                     |   School Admin    |
                     |                   |
                     +--------+----------+
                              |
                              | Manages Users
                              | & System Settings
                              v
+---------------+    +------------------+    +-----------------+
|               |    |                  |    |                 |
|   Students    +--->+  School Item     +<---+    Teachers    |
|               |    |  Exchange App    |    |                 |
+---------------+    +------------------+    +-----------------+
  List/Buy/Donate      ^            ^        List/Buy/Donate
  Items & Participate  |            |        Items & Create
  in Events            |            |        Events
                       |            |
           +-----------+            +------------+
           |                                     |
+----------+-----------+              +----------+----------+
|                      |              |                     |
|  Student Councils    |              |    School Clubs     |
|  & Organizations     |              |                     |
+----------------------+              +---------------------+
      Create & Manage Events                Create & Manage Events
```

## Level 0 Data Flow Diagram (DFD)

```
                                +---------------------+
                                |                     |
       +----------------------->|  User Management    |
       |                        |                     |
       |                        +----------+----------+
       |                                   |
       |                                   | User Data
       |                                   v
+------+-------+                 +---------+---------+
|              |   Credentials   |                   |
|    Users     +---------------->|  Authentication   |
|              |                 |                   |
+------+-------+                 +---------+---------+
       |                                   |
       | Listings                          | Authenticated
       | Transactions                      | User
       v                                   v
+------+------------------------+----------+----------+
|                                                     |
|               Item Management System                |
|                                                     |
+---+-------------------------+---------------------+-+
    |                         |                     |
    | Item Data               | Item Data           | Transaction
    |                         |                     | Data
    v                         v                     v
+---+-----------+   +---------+---------+   +-------+---------+
|               |   |                   |   |                 |
| Item Database |   |  Event Database   |   |  Transaction    |
|               |   |                   |   |  Database       |
+---------------+   +-------------------+   +-----------------+
```

## Level 1 Data Flow Diagram (DFD) - Item Management System

```
+---------------+          +-----------------+
|               |          |                 |
| User Interface+--------->| Item Creation   |
|               |          |                 |
+-------+-------+          +--------+--------+
        |                           |
        |                           | New Item
        |                           v
        |                  +--------+--------+
        |                  |                 |
        |                  | Item Moderation |
        |                  |                 |
        |                  +--------+--------+
        |                           |
        |                           | Approved Item
        |                           v
        |                  +--------+--------+
        |                  |                 |
        +----------------->| Item Listing    |
        |                  |                 |
        |                  +--------+--------+
        |                           |
        | Search/Browse             | Available
        |                           | Items
        v                           v
+-------+-------+          +--------+--------+
|               |          |                 |
| Search System |          | Transaction     |
|               |          | Processing      |
+---------------+          |                 |
                           +-----------------+
```

## User Role Hierarchy

```
                      +------------+
                      |            |
                      |   Admin    |
                      |            |
                      +------+-----+
                             |
                             | Supervises
                             v
              +-------------+-------------+
              |                           |
      +-------v-------+           +-------v-------+
      |               |           |               |
      |   Moderator   |           |   Teacher     |
      |               |           |               |
      +-------+-------+           +-------+-------+
              |                           |
              | Approves Items            | Creates Events
              |                           |
              v                           v
      +-------+-------------------------+-+
      |                                   |
      |           Student                 |
      |                                   |
      +-----------------------------------+
```