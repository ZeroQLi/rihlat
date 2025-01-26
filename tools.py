import requests
import streamlit as st

from datetime import datetime
from typing import Optional, Type, Dict
from agents import GTFSQueryAgent
from langchain.tools import BaseTool
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from pydantic import BaseModel, Field

class GTFSCoordInput(BaseModel):
    query: str = Field(description="User Query")

class GTFSCoordinatorTool(BaseTool):
    name: str = "gtfs_coordinator"
    description: str = "Handles queries related to public transit data, such as schedules, routes, and stop information"
    args_schema: Type[BaseModel] = GTFSCoordInput
    return_direct: bool = True

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        db_path = "merged_gtfs.db"  # Direct path to the merged GTFS database

        try:
            agent = GTFSQueryAgent(db_path)
            result = agent.write_query(query)
            return result
        except Exception as e:
            if run_manager:
                run_manager.on_tool_error(e)
            return f"Error: {str(e)}"
    
    async def _arun(
        self, 
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        db_path = "merged_gtfs.db"  # Direct path to the merged GTFS database

        try:
            agent = GTFSQueryAgent(db_path)
            result = agent.write_query(query)  
            if run_manager:
                await run_manager.on_tool_end(result)
            return result
        except Exception as e:
            if run_manager:
                await run_manager.on_tool_error(e)
            return f"Error: {str(e)}"


class GeocodingInput(BaseModel):
    query: str = Field(description="Location to search for (e.g., 'Amsterdam')")
    lat: Optional[float] = Field(default=None, description="Latitude of the search area center")
    lon: Optional[float] = Field(default=None, description="Longitude of the search area center")
    radius: Optional[int] = Field(default=None, description="Radius around the lat/lon in meters")
    limit: Optional[int] = Field(default=10, description="Maximum number of results to return")
    countrySet: Optional[str] = Field(default=None, description="Comma-separated list of country codes (e.g., 'US,NL')")
    language: Optional[str] = Field(default="en", description="Language for the results")
    ext: str = Field(default="json", description="Response format, usually 'json'")

class GeocodingTool(BaseTool):
    name: str = "geocoding_tool"
    description: str = "Fetches geocoding information from TomTom's API based on user inputs"
    args_schema: Type[BaseModel] = GeocodingInput
    return_direct: bool = True

    def _run(
        self,
        query: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None,
        limit: Optional[int] = 10,
        countrySet: Optional[str] = None,
        language: Optional[str] = "en-US",  # Use valid language tag
        ext: str = "json",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        try:
            # Get the API key from Streamlit secrets
            api_key = st.secrets.get("TOMTOM_API_KEY", None)
            if not api_key:
                return {"error": "API key is missing from secrets.toml"}

            # Construct the API URL
            base_url = "https://api.tomtom.com/search/2/geocode"
            params = {
                "key": api_key,
                "limit": limit,
                "language": language,  # Valid language tag
                "lat": lat,
                "lon": lon,
                "radius": radius,
                "countrySet": countrySet,
            }

            # Construct the request URL
            request_url = f"{base_url}/{query}.{ext}"
            print(f"Request URL: {request_url}")

            # Make the API request
            response = requests.get(request_url, params={k: v for k, v in params.items() if v is not None})
            print(f"Response Status: {response.status_code}")

            if response.status_code != 200:
                return {"error": f"API call failed with status code {response.status_code}: {response.text}"}

            return response.json()

        except Exception as e:
            return {"error": str(e)}

    async def _arun(
        self,
        query: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None,
        limit: Optional[int] = 10,
        countrySet: Optional[str] = None,
        language: Optional[str] = "en",
        ext: str = "json",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Dict:
        try:
            return self._run(query, lat, lon, radius, limit, countrySet, language, ext)
        except Exception as e:
            return {"error": str(e)}

class CurrentDateTime(BaseTool):
    name: str = "curren_datetime"
    description: str = "Provides the current date and time."

    def _run(
        self, query: Optional[str] = None, run_manager: Optional[object] = None
    ) -> str:
        """
        Run the tool synchronously to fetch the current date and time.
        """
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"The current date and time is: {current_time}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _arun(
        self, query: Optional[str] = None, run_manager: Optional[object] = None
    ) -> str:
        """
        Run the tool asynchronously to fetch the current date and time.
        """
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"The current date and time is: {current_time}"
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    tool = GTFSCoordinatorTool()
    response = tool._run()

