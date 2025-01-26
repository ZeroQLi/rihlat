import sqlite3
import streamlit as st
from typing import Dict
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase

class GTFSQueryAgent:
    def __init__(self, db_path: str, top_k: int = 5):
        """
        Initializes the GTFSQueryAgent.

        :param db_path: Path to the merged SQLite database.
        :param top_k: The maximum number of results to return in a query.
        """
        self.db_path = db_path
        self.top_k = top_k
        self._model = None
        self._sys_msg = None
        self._hum_msg = None
        self._table_info = None

    @property
    def model(self):
        if self._model is None:
            self._model = ChatOpenAI(
                base_url="https://api.sambanova.ai/v1/",
                api_key=st.secrets["SAMBANOVA_API_KEY"],  # Replace with your API key
                streaming=True,
                model="Meta-Llama-3.1-70B-Instruct",
            )
        return self._model

    @property
    def sys_msg(self):
        if self._sys_msg is None:
            self._sys_msg = SystemMessagePromptTemplate.from_template(
                """
                You are a SQL generation assistant. Your task is to generate SQL queries to answer user questions.
                Follow these instructions:

                1. Identify the most relevant tables in the database schema based on the user's question. Use only the tables provided in the schema.
                2. Generate a valid SQL query using the `sqlite` dialect.
                3. Do not include any Markdown formatting such as triple backticks (` ``` `) or tags like `sql` in the output.
                4. Ensure the SQL query is syntactically correct and limited to {top_k} results unless otherwise specified by the user.
                
                Additional Information:
                - Common Transit Names (E101, MGrn, etc.) can be found in the routes table -> route_short_name column
                - Common Stop Names (Dubai Mall, MS, Dubai Studio City, etc.) can be found in the routes table -> route_long_name column

                Use the following database schema information for `merged_gtfs.db`:
                {table_info}

                Question:
                {input}
                """
            )
        return self._sys_msg

    @property
    def hum_msg(self):
        if self._hum_msg is None:
            self._hum_msg = HumanMessagePromptTemplate.from_template(
                "Database Schema:\n{table_info}\n\nQuestion: {input}"
            )
        return self._hum_msg

    @property
    def table_info(self):
        if self._table_info is None:
            # Get the table info from the merged database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_info = "\n\n".join(
                [f"Database: merged_gtfs.db\nTable: {table[0]}\n{self.get_table_info(table[0], conn)}" for table in tables]
            )
            conn.close()
            self._table_info = table_info
        return self._table_info

    def get_table_info(self, table_name: str, conn):
        """Returns the schema info of the specified table."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        return "\n".join([f"Column: {col[1]}, Type: {col[2]}" for col in columns])

    def run_query(self, query: str):
        """
        Executes a query on the merged SQLite database and returns the results.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            return results
        except sqlite3.Error as e:
            return {"errors": f"SQLite error: {str(e)}"}

    def write_query(self, question: str) -> Dict:
        """
        Generates and executes a SQL query based on the input question.

        :param question: The natural language question to answer using SQL.
        :return: A dictionary containing the query, results, and any errors.
        """
        query_prompt = ChatPromptTemplate.from_messages([self.sys_msg, self.hum_msg])
        prompt = query_prompt.invoke(
            {
                "dialect": "sqlite",
                "top_k": self.top_k,
                "table_info": self.table_info,
                "input": question,
            }
        )

        try:
            response = self.model.invoke(prompt).content
            print(response)
            query = response.strip()

            # Execute the SQL query on the 'merged_gtfs.db'
            results = self.run_query(query)

            return {
                "query": query,
                "results": results,
                "errors": None,
            }
        except Exception as e:
            return {
                "query": None,
                "results": None,
                "errors": str(e),
            }

