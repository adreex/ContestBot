import sqlite3


class DBHelper:
    def __init__(self, name='userdata.sqlite'):
        self.name = name
        self.conn = sqlite3.connect(name)

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, ttype, value, traceback):
        self.close()

    def setup(self):
        self.conn.execute('CREATE TABLE IF NOT EXISTS userdata ('
                          'user_id INTEGER NOT NULL PRIMARY KEY UNIQUE,'
                          'subscribed INTEGER NOT NULL DEFAULT 0);')
        self.conn.commit()

    def get_users(self):
        return [x[0] for x in self.conn.execute('SELECT user_id FROM userdata')]

    def add_user(self, user_id):
        if not self.check_user(user_id):
            stat = 'INSERT INTO userdata (user_id) VALUES (?)'
            self.conn.execute(stat, [user_id])
            self.conn.commit()

    def del_user(self, user_id):
        stat = 'DELETE FROM userdata WHERE user_id = (?)'
        if self.check_user(user_id):
            self.conn.execute(stat, [user_id])
            self.conn.commit()

    def check_user(self, user_id):
        stat = 'SELECT user_id FROM userdata WHERE user_id = (?)'
        if len([x[0] for x in self.conn.execute(stat, [user_id])]):
            return True

    def get_amount_of_users(self):
        stat = 'SELECT Count(*) FROM userdata'
        result = self.conn.execute(stat)
        return result.fetchone()[0]

    def set(self, user_id, item, data):
        if self.check_user(user_id):
            stat = f'UPDATE userdata SET {item} = (?) WHERE user_id = (?)'
            self.conn.execute(stat, (data, user_id))
            self.conn.commit()

    def get(self, user_id, item):
        if self.check_user(user_id):
            stat = f'SELECT {item} FROM userdata WHERE user_id = (?)'
            result = self.conn.execute(stat, [user_id]).fetchone()
            if result:
                return result[0]

    def get_participants_amount(self):
        stat = 'SELECT Count(*) FROM userdata WHERE subscribed = 1'
        result = self.conn.execute(stat)
        return result.fetchone()[0]

    def get_winner(self):
        stat = f'SELECT * FROM userdata WHERE subscribed = 1 ORDER BY RANDOM() LIMIT 1'
        result = self.conn.execute(stat)
        return [user[0] for user in result.fetchall()]

    def close(self):
        self.conn.close()
