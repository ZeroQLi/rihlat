import requests

from typing import Optional, Type
from agents import GTFSQueryAgent, GeocodingAgent
from langchain.tools import BaseTool
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field
from langchain_community.utilities import SQLDatabase

class GTFSCoordInput(BaseModel):
    question: str = Field(description="User Query")
    databases: dict = Field(description="Database Dictionary")
    top_k: int = Field(description="Top K Results")

class GeocodeInput(BaseModel):
    query: str = Field(description="The location or address to geocode.")
    limit: int = Field(default=1, description="Maximum number of results to return.")
    country_set: Optional[str] = Field(
        default=None, description="Restrict search to specific countries (comma-separated ISO 3166-1 alpha-2 codes)."
    )
    language: str = Field(default="en", description="Preferred language for the results.")

class GTFSCoordinatorTool(BaseTool):
    name: str = "gtfs_coordinator"
    description: str = "Handles queries related to public transit data, such as schedules, routes, and stop information"
    args_schema: Type[BaseModel] = GTFSCoordInput
    return_direct: bool = True

    def _run(
        self, question: str, databases: dict, top_k: int, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        try:
            agent = GTFSQueryAgent(databases, top_k)
            return agent.write_query(question)
        except Exception as e:
            if run_manager:
                run_manager.on_tool_error(e)
            return f"Error: {str(e)}"
    
    async def _arun(
        self, 
        question: str, 
        databases: dict, 
        top_k: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        try:
            agent = GTFSQueryAgent(databases, top_k)
            result = agent.write_query(question)  
            if run_manager:
                await run_manager.on_tool_end(result)
            return result
        except Exception as e:
            if run_manager:
                await run_manager.on_tool_error(e)
            return f"Error: {str(e)}"

class GeocodingTool(BaseTool):
    name: str = "geocoding_tool"
    description: str = (
        "Uses a geocoding agent to resolve natural language location queries into coordinates, addresses, and entities. "
        "It can handle optional restrictions like country-specific searches and language preferences."
    )
    args_schema: Type[BaseModel] = GeocodeInput
    return_direct: bool = True  # Create an instance of the GeocodingAgent here

    def _run(
        self, 
        query: str, 
        limit: int = 1, 
        country_set: Optional[str] = None, 
        language: str = "en", 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """
        Synchronous execution of the tool.

        :param query: The location or address to geocode.
        :param limit: Maximum number of results to return.
        :param country_set: Restrict search to specific countries.
        :param language: Preferred language for the results.
        :return: Geocoding results as a string.
        """
        try:
            agent = GeocodingAgent()
            result = agent.geocode(query=query, limit=limit, country_set=country_set, language=language)
            if result["errors"]:
                return f"Error: {result['errors']}"
            return str(result["results"])
        except Exception as e:
            if run_manager:
                run_manager.on_tool_error(e)
            return f"Error: {str(e)}"

    async def _arun(
        self, 
        query: str, 
        limit: int = 1, 
        country_set: Optional[str] = None, 
        language: str = "en", 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """
        Asynchronous execution of the tool.

        :param query: The location or address to geocode.
        :param limit: Maximum number of results to return.
        :param country_set: Restrict search to specific countries.
        :param language: Preferred language for the results.
        :return: Geocoding results as a string.
        """
        try:
            result = self.agent.geocode(query=query, limit=limit, country_set=country_set, language=language)
            if result["errors"]:
                return f"Error: {result['errors']}"
            return str(result["results"])
        except Exception as e:
            if run_manager:
                await run_manager.on_tool_error(e)
            return f"Error: {str(e)}"

# if __name__ == "__main__":
#     db_names = ['routes', 'stops', 'stop_times', 'transfers', 'trips']
#     sql_dict = {
#         name : SQLDatabase.from_uri(f"sqlite:///databases/{name}.db") 
#         for name in db_names
#     }
#     question = "Give me all unique short route names"
#     tool = GTFSCoordinatorTool()
#     print(tool.invoke(
#         {
#             "question":question,
#             "databases":sql_dict,
#             "top_k":5,
#         }
#     ))

if __name__ == "__main__":
    
    tool = GeocodingTool()
    print(tool.invoke({
        "query": "Where is the statue of liberty?",
        "limit": 2,
        "country_set": "US",
        "language": "en",
    }))