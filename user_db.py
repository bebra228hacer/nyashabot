import aiosqlite
import os
import asyncio
import json 
from dotenv import load_dotenv
from datetime import datetime, timedelta


load_dotenv()
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(os.environ.get("DEBUG"))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
MAX_CONTEXT = int(os.environ.get("MAX_CONTEXT"))


class User:
    def __init__(
        self,
        id,
        name=None,
        prompt=[],
        remind_of_yourself= "2077-06-15 22:03:51",  
        sub_lvl=0,
        sub_id=0,
        sub_period=-1,
        is_admin=0,
    ):
        self.id = id
        self.name = name
        self.prompt = prompt
        self.remind_of_yourself = remind_of_yourself
        self.sub_lvl = sub_lvl
        self.sub_id = sub_id
        self.sub_period = sub_period
        self.is_admin = is_admin

    def __repr__(self):
        return f"User(id={self.id}, \n name={self.name}, \n prompt={self.prompt}, \n remind_of_yourself={self.remind_of_yourself}, \n sub_lvl={self.sub_lvl}, \n sub_id={self.sub_id}, \n sub_period={self.sub_period}, \n is_admin={self.is_admin})"

    async def get_from_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql = f"SELECT * FROM {TABLE_NAME} WHERE id = ?"
            await cursor.execute(sql, (self.id,))
            row = await cursor.fetchone()
            if row:
                self.id = row[0]
                self.name = row[1]
                self.prompt = json.loads(row[2])
                self.remind_of_yourself = row[3]  
                self.sub_lvl = row[4]
                self.sub_id = row[5]
                self.sub_period = row[6]
                self.is_admin = row[7]

    async def __call__(self, user_id):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql = f"SELECT * FROM {TABLE_NAME} WHERE id = ?"
            await cursor.execute(sql, (user_id,))
            row = await cursor.fetchone()
            if row:
                user = User(
                    id=row[0],
                    name=row[1],
                    prompt=json.loads(row[2]),
                    remind_of_yourself=row[3], 
                    sub_lvl=row[4],
                    sub_id=row[5],
                    sub_period=row[6],
                    is_admin=row[7],
                )
                return user
            else:
                return None

    async def save_for_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql_insert = f"""
                        INSERT INTO {TABLE_NAME} (id, name, prompt, remind_of_yourself, sub_lvl, sub_id, sub_period, is_admin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
            values = (
                self.id,
                self.name,
                json.dumps(self.prompt),
                self.remind_of_yourself, 
                self.sub_lvl,
                self.sub_id,
                self.sub_period,
                self.is_admin,
            )
            await cursor.execute(sql_insert, values)
            await db.commit()
            await cursor.close()

    async def update_prompt(self, role, new_request):
        new_entry = {"role": role, "content": new_request}
        self.prompt.append(new_entry)
        if len(self.prompt) > MAX_CONTEXT:
            self.prompt = self.prompt[-MAX_CONTEXT:]

    async def update_in_db(self):
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.cursor()
            sql_query = f"""
                UPDATE {TABLE_NAME}
                SET name = ?, prompt = ?, remind_of_yourself = ?, sub_lvl = ?, sub_id = ?, sub_period = ?, is_admin = ?
                WHERE id = ?
            """
            values = (
                self.name,
                json.dumps(self.prompt),
                self.remind_of_yourself, 
                self.sub_lvl,
                self.sub_id,
                self.sub_period,
                self.is_admin,
                self.id,
            )
            await cursor.execute(sql_query, values)
            await db.commit()
            await cursor.close()

async def check_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY,  --  ID is now the PRIMARY KEY and NOT AUTOINCREMENT
                    name TEXT,
                    prompt JSON,
                    remind_of_yourself TEXT,
                    sub_lvl INTEGER,
                    sub_id TEXT,
                    sub_period INTEGER,
                    is_admin INTEGER
                )
                """
            )
        await db.commit()
        return "Бд подгружена успешно"


async def user_exists(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.cursor()
        sql = f"SELECT EXISTS(SELECT 1 FROM {TABLE_NAME} WHERE id = ?)"
        await cursor.execute(sql, (user_id,))
        result = (await cursor.fetchone())[0]
        await cursor.close()
    await db.close()

    return bool(result)

async def time_after(after_an):
    now = datetime.now()
    future_time = now + timedelta(hours=after_an)
    if 21 <= now.hour or now.hour < 6: 
        future_time = future_time.replace(hour=6, minute=0, second=0, microsecond=0)
    formatted_future_time = future_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_future_time
    
async def get_past_dates():
    past_user_ids = []
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("PRAGMA journal_mode=WAL;") as cursor:
            await cursor.fetchone()

        now = datetime.now()

        query = f"SELECT {"id"}, {"remind_of_yourself"} FROM {TABLE_NAME}"

        async with db.execute(query) as cursor:
            results = await cursor.fetchall()
        for row in results:
            user_id = row[0]  
            date_str = row[1]
            date_from_db = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            if date_from_db < now:
                past_user_ids.append(user_id) 

    return past_user_ids




async def main():
    print(await time_after(2))
    


if __name__ == "__main__":
    asyncio.run(main())
