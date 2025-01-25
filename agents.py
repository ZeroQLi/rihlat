import requests
import streamlit as st

from typing import Dict, Optional
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from pydantic import BaseModel

class GTFSQueryAgent:
    def __init__(self, databases: Dict[str, SQLDatabase], top_k: int):
        """
        Initializes the GTFSQueryAgent.

        :param databases: Dictionary of SQLDatabase objects keyed by database names.
        :param top_k: The maximum number of results to return in a query.
        """
        self.databases = databases
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
                api_key=st.secrets["SAMBANOVA_API_KEY"], 
                streaming=True,
                model="Meta-Llama-3.1-8B-Instruct",
            )
        return self._model

    @property
    def sys_msg(self):
        if self._sys_msg is None:
            self._sys_msg = SystemMessagePromptTemplate.from_template(
                """
                Given an input question, create a syntactically correct {dialect} query to run to help find the answer.
                Unless the user specifies in their question a specific number of examples, always limit your query to at most {top_k} results.
                Pay attention to use only the column names that you can see in the schema description.
                Prefix each query with the correct database name in the following format:

                <database_name>|<SQL query>

                Only use the following tables:
                {table_info}

                Question: {input}
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
            self._table_info = "\n\n".join(
                [
                    f"Database: {name}\n{db.get_table_info()}"
                    for name, db in self.databases.items()
                ]
            )
        return self._table_info

    def write_query(self, question: str) -> Dict:
        """
        Generates and executes a SQL query based on the input question.

        :param question: The natural language question to answer using SQL.
        :return: A structured dictionary containing the query, database, results, and metadata.
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
            database, query = response.split("|")
            database = database.strip()
            query = query.strip()

            if database not in self.databases:
                return {
                    "errors": f"Database '{database}' not found in available databases.",
                }

            results = self.databases[database].run(query)

            return {
                "query": query,
                "database": database,
                "results": results,
                "errors": None,
            }
        except ValueError as e:
            return {
                "errors": f"Invalid model response format: {str(e)}",
            }
        except Exception as e:
            return {
                "errors": str(e),
            }

class GeocodingAgent:
    def __init__(self, base_url: str = "https://api.tomtom.com"):
        """
        Initializes the GeocodingAgent.

        :param base_url: Base URL for the TomTom API.
        """
        self.base_url = base_url
        self._model = None
        self._sys_msg = None
        self._hum_msg = None

    @property
    def model(self):
        if self._model is None:
            self._model = ChatOpenAI(
                base_url="https://api.sambanova.ai/v1/",
                api_key=st.secrets["SAMBANOVA_API_KEY"], 
                streaming=True,
                model="Meta-Llama-3.1-70B-Instruct",
            )
        return self._model

    @property
    def sys_msg(self):
        if self._sys_msg is None:
            self._sys_msg = SystemMessagePromptTemplate.from_template(
                """
                You are an assistant that processes geocoding queries to extract relevant information for making an API request to a geocoding service. 
                Your task is to identify the key details in the user's query and organize them into the appropriate parameters.

                For each query:
                1. Extract the location's name (e.g., landmark, address, or place name).
                2. Identify the city and country (if mentioned). If not explicitly mentioned, infer from context.
                3. Determine the limit on the number of results (if specified).
                4. Identify the language preference (if provided).
                5. Consider country restrictions and adjust the query for geocoding accuracy.

                Return only these parameteres as a dictionary. Do not include any additional explanations.

                Here are some examples of how the query and parameters should be structured:
                - Query: "Eiffel Tower, Paris, France" → Parameters: Location = "Eiffel Tower, Paris, France", Limit = 1, Language = "en", CountrySet = "FR"
                - Query: "Central Park, New York" → Parameters: Location = "Central Park, New York", Limit = 1, Language = "en", CountrySet = "US"
                - Query: "Statue of Liberty" → Parameters: Location = "Statue of Liberty, New York, US", Limit = 1, Language = "en", CountrySet = "US"

                Ensure that all extracted details are correctly formatted for the API and that irrelevant information is excluded.
                """
            )
        return self._sys_msg

    @property
    def hum_msg(self):
        if self._hum_msg is None:
            self._hum_msg = HumanMessagePromptTemplate.from_template(
                """
                User Query: {query}
                Limit: {limit}
                Country Restriction: {country_set}
                Language: {language}
                """
            )
        return self._hum_msg

    def preprocess_query(self, query: str, limit: int, country_set: Optional[str], language: str) -> str:
        """
        Uses the LLM to preprocess the user's natural language query into a refined format.

        :param query: The user's geocoding query in natural language.
        :param limit: Maximum number of results to return.
        :param country_set: Restriction to specific countries (optional).
        :param language: Preferred language for the results.
        :return: A refined query string.
        """
        query_prompt = ChatPromptTemplate.from_messages([self.sys_msg, self.hum_msg])
        prompt = query_prompt.invoke(
            {
                "query": query,
                "limit": limit,
                "country_set": country_set or "None",
                "language": language,
            }
        )
        response = self.model.invoke(prompt).content.strip()
        print(response)
        return response

    def call_tomtom_api(self, query: str, limit: int, country_set: Optional[str], language: str) -> Dict:
        """
        Calls the TomTom API to fetch geocoding results.

        :param query: The refined query.
        :param limit: Maximum number of results to return.
        :param country_set: Restriction to specific countries (optional).
        :param language: Preferred language for the results.
        :return: A dictionary containing the API response.
        """
        url = f"{self.base_url}/search/2/geocode/{requests.utils.quote(query)}.json"
        params = {
            "key": st.secrets["TOMTOM_API_KEY"],
            "limit": limit,
            "countrySet": country_set,
            "language": language,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def geocode(self, query: str, limit: int = 1, country_set: Optional[str] = None, language: str = "en") -> Dict:
        """
        Main method that preprocesses the user's query, calls the TomTom API, and returns results.

        :param query: The user's geocoding query.
        :param limit: Maximum number of results to return.
        :param country_set: Restriction to specific countries (optional).
        :param language: Preferred language for the results.
        :return: A structured dictionary containing the query, results, and errors (if any).
        """
    
        # Preprocess the query
        refined_query = self.preprocess_query(query, limit, country_set, language)

        # Call the TomTom API
        api_response = self.call_tomtom_api(refined_query, limit, country_set, language)

        return api_response

            