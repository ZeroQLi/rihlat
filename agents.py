import requests
import sqlite3
import streamlit as st
from typing import Dict, List
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI

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
        self._initialized = False

    def _initialize(self):
        """Initializes system and human messages, model, and table information."""
        if not self._initialized:
            print("Initializing the agent...")

            # Initialize system and human message templates
            self._sys_msg = SystemMessagePromptTemplate.from_template(
                """
                You are a SQL generation assistant. Your task is to generate SQL queries to answer user questions.
                Follow these instructions:

                1. Identify the most relevant tables in the database schema based on the user's question. Use only the tables provided in the schema.
                2. Generate a valid SQL query using the `sqlite` dialect.
                3. Do not include any Markdown formatting such as triple backticks (` ``` `) or tags like `sql` in the output.
                4. Ensure the SQL query is syntactically correct and limited to {top_k} results unless otherwise specified by the user.
                5. Only return the SQL query.
                
                Additional Information:
                - Common Transit Names (E101, MGrn, etc.) can be found in the routes table -> route_short_name column
                - Common Stop Names (Dubai Mall, MS, Dubai Studio City, etc.) can be found in the routes table -> route_long_name column

                Refrain from adding any additional information.
                Use the following database schema information for `merged_gtfs.db`:
                {table_info}

                Question:
                {input}
                """
            )

            self._hum_msg = HumanMessagePromptTemplate.from_template(
                "Database Schema:\n{table_info}\n\nQuestion: {input}"
            )

            # Initialize model
            self._model = ChatOpenAI(
                base_url="https://api.sambanova.ai/v1/",
                api_key=st.secrets["SAMBANOVA_API_KEY"], 
                streaming=True,
                model="Meta-Llama-3.1-70B-Instruct",
            )

            # Initialize table info
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_info = "\n\n".join(
                [f"Database: merged_gtfs.db\nTable: {table[0]}\n{self.get_table_info(table[0], conn)}" for table in tables]
            )
            conn.close()
            self._table_info = table_info

            # Mark the agent as initialized
            self._initialized = True

    @property
    def table_info(self):
        """Property for table_info, initialized only when needed."""
        self._initialize()  # Ensure initialization happens
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
        # Initialize the agent (model, messages, table info)
        self._initialize()

        query_prompt = ChatPromptTemplate.from_messages([self._sys_msg, self._hum_msg])
        prompt = query_prompt.invoke(
            {
                "dialect": "sqlite",
                "top_k": self.top_k,
                "table_info": self._table_info,
                "input": question,
            }
        )
        try:
            response = self._model.invoke(prompt).content
            query = response.strip()
            print(query)
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
        
class RoutesAgent:
    def __init__(self):
        self.base_url = "http://dev.virtualearth.net/REST/v1/Routes/transit"
        self.initialized = False

    def initialize(self):
        """Initializes the agent's components."""
        if not self.initialized:
            print("Initializing the RoutesAgent...")

            # Initialize model
            self.model = ChatOpenAI(
                base_url="https://api.sambanova.ai/v1/",
                api_key=st.secrets["SAMBANOVA_API_KEY"],
                streaming=True,
                model="Meta-Llama-3.1-70B-Instruct",
            )

            # Initialize system and human messages
            self.sys_msg = SystemMessagePromptTemplate.from_template(
                """
                You are a Routes API Agent responsible for extracting all location mentions from the user's query. 

                Instructions:
                - Identify all locations mentioned in the query.
                - Return the results only as a Python list of waypoints: [waypoint1, waypoint2, ...].
                - Refrain from adding any additional information or commentary.

                Question:
                {input}
                """
            )

            self.hum_msg = HumanMessagePromptTemplate.from_template(
                "Question: {input}"
            )

            # Mark the agent as initialized
            self.initialized = True

    def extract_locations(self, question: str) -> List[str]:
        """Extracts locations from the question using the agent's model."""
        self.initialize()  # Ensure initialization happens

        query_prompt = ChatPromptTemplate.from_messages([self.sys_msg, self.hum_msg])
        prompt = query_prompt.invoke({"input": question})

        response = self.model.invoke(prompt).content
        return eval(response.strip())  
    
    def fetch_response(self, 
                       question,
                       optimize: str = "time", 
                       avoid: str = None, 
                       distance_unit: str = "km", 
                       date_time: str = None, 
                       max_solutions: int = None) -> Dict:
        """Fetches a response from the Routes API based on the extracted locations."""
        try:
            self.initialize()  # Ensure initialization happens

            api_key = st.secrets["BINGMAPS_KEY"]
            if not api_key:
                return {"error": "API key is missing. Provide it in secrets or as an input parameter."}
            
            params = {
                "optimize": optimize,
                "avoid": avoid,
                "distanceUnit": distance_unit,
                "dateTime": date_time,
                "maxSolutions": max_solutions,
                "key": st.secrets["BINGMAPS_KEY"],
            }
            
            # Extract locations from the question
            waypoints = self.extract_locations(question)
            
            for i, waypoint in enumerate(waypoints, start=1):
                params[f"waypoint.{i}"] = waypoint
            
            response = requests.get(self.base_url, params={k: v for k, v in params.items() if v is not None})
            
            if response.status_code != 200:
                return {"error": f"API call failed with status code {response.status_code}: {response.text}"}
            
            response = response.json()
            itinerary_items = response['resourceSets'][0]['resources'][0]['routeLegs'][0]['itineraryItems']
            
            instructions = [item['instruction']['text'] for item in itinerary_items]

            results = {
                "start_coords": response['resourceSets'][0]['resources'][0]['routeLegs'][0]['actualStart'],
                "end_coords": response['resourceSets'][0]['resources'][0]['routeLegs'][0]['actualEnd'],
                "travelDistance": response['resourceSets'][0]['resources'][0]['travelDistance'],
                "travelDuration": response['resourceSets'][0]['resources'][0]['travelDuration'],
                "instructions": instructions
            }

            return results
        
        except Exception as e:
            return {
                "start_coords" : None,
                "end_coords" : None,
                "travelDistance" : None,
                "travelDuration" : None,
                "instructions" : [],
            }

if __name__ == '__main__':
    agent = GTFSQueryAgent("merged_gtfs.db")
    print(agent.write_query("What is the nearest bus stop from Abu Dhabi Mall?"))