import aiosqlite
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(os.environ.get("DEBUG"))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME =  os.environ.get("TABLE_NAME")

class User:
    def __init__(self, id, name=None, sub_lvl=0, sub_period=-1, is_admin=0):
        self.id = id
        self.name = name
        self.sub_lvl = sub_lvl
        self.sub_period = sub_period
        self.is_admin = is_admin

    def __repr__(self):
        return f"User(id={self.id}, name='{self.name}', sub_lvl={self.sub_lvl}, sub_period={self.sub_period}, is_admin={self.is_admin})"

    async def save_for_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql_insert = f"""
                        INSERT INTO {TABLE_NAME} (id, name, sub_lvl, sub_period, is_admin)
                        VALUES (?, ?, ?, ?, ?)
                    """
            values = (self.id, self.name, self.sub_lvl, self.sub_period, self.is_admin)
            await cursor.execute(sql_insert, values)
            await db.commit()
            await cursor.close()
    
    async def get_from_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql = f"SELECT * FROM {TABLE_NAME} WHERE id = ?"
            await cursor.execute(sql, (self.id,))
            row = list(await cursor.fetchone())
            if row:
                self.id = row[0]
                self.name = row[1]
                self.sub_lvl = row[2]
                self.sub_period = row[3]
                self.is_admin = row[4]
            await db.close()
            
    
    async def update_in_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql_query = f"""
                UPDATE {TABLE_NAME}
                SET name = ?, sub_lvl = ?, sub_period = ?, is_admin = ?
                WHERE id = ?
            """
            values = (self.name, self.sub_lvl, self.sub_period, self.is_admin, self.id)
            await cursor.execute(sql_query, values) 
            await db.commit() 
            await cursor.close()
        await db.close()


async def main():
    Test = User(id = 1)
    await Test.get_from_db()
    print(Test)
    Test2 = User(5)
    await Test2.get_from_db()
    print(Test2)
    Test3 = User(2)
    
    Test3.is_admin = 1
    Test3.name = "LOL"
    await Test3.update_in_db()
    print(Test3)
    pass

if __name__ == "__main__":
    asyncio.run(main())
