CREATE TABLE users (id INTEGER, username TEXT NOT NULL, hash TEXT NOT NULL, cash NUMERIC NOT NULL DEFAULT 10000.00, PRIMARY KEY(id));
CREATE UNIQUE INDEX username ON users (username);
CREATE TABLE wallet (id INTEGER, symbol TEXT, name TEXT, price NUMERIC, length INTEGER, user_id INTEGER, PRIMARY KEY(id), FOREIGN KEY (user_id) REFERENCES users(id));
CREATE TABLE transactions (id INTEGER, symbol TEXT, shares INTEGER, price NUMERIC, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id));