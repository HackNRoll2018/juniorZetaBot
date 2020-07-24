import json
import sqlite3

DELIMITER = ' | '


class DBHelper:
    def __init__(self):
        with open('config.json') as config_file:
            config = json.load(config_file)
        self.dbname = config['db']
        self.conn = sqlite3.connect(self.dbname)
        self.table = config['db_table']

    def setup(self):
        statement = f"""CREATE TABLE IF NOT EXISTS {self.table} (logID INTEGER PRIMARY KEY, timestamp text, description text)"""
        self.conn.execute(statement)
        self.conn.commit()

    def add_log(self, timestamp, description):
        statement = f"""INSERT INTO {self.table} (timestamp, description) VALUES (?, ?)"""
        args = (str(timestamp), str(description),)
        self.conn.execute(statement, args)
        self.conn.commit()

    def delete_log(self, timestamp):
        statement = f"""DELETE FROM {self.table} WHERE timestamp = (?)"""
        args = (str(timestamp),)
        self.conn.execute(statement, args)
        self.conn.commit()

    def get_latest_log(self):
        statement = f"""SELECT timestamp, description FROM {self.table} WHERE logID = (SELECT MAX(logID) FROM {self.table})"""
        return [DELIMITER.join(x) for x in self.conn.execute(statement)]
