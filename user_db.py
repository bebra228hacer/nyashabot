import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(os.environ.get("DEBUG"))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME =  os.environ.get("TABLE_NAME")

class User:
    def __init__(self, id=None, name=None, sub_lvl=0, sub_period=-1, is_admin=0):
        self.id = id
        self.name = name
        self.sub_lvl = sub_lvl
        self.sub_period = sub_period
        self.is_admin = is_admin

    def __repr__(self):
        return f"User(id={self.id}, name='{self.name}', sub_lvl={self.sub_lvl}, sub_period={self.sub_period}, is_admin={self.is_admin})"

    async def save(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            async with db.cursor() as cursor:
                if self.id is None:
                    await cursor.execute(
                        f"INSERT INTO {TABLE_NAME} (name, sub_lvl, sub_period, is_admin) VALUES (?, ?, ?, ?)",
                        (self.name, self.sub_lvl, self.sub_period, self.is_admin),
                    )
                    self.id = cursor.lastrowid
                else:
                    await cursor.execute(
                        f"UPDATE {TABLE_NAME} SET name=?, sub_lvl=?, sub_period=?, is_admin=? WHERE id=?",
                        (self.name, self.sub_lvl, self.sub_period, self.is_admin, self.id),
                    )
            await db.commit()

    async def delete(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            async with db.cursor() as cursor:
                await cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE id=?", (self.id,))
            await db.commit()
        self.id = None