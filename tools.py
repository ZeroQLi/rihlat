import os
import pytz
import requests
import streamlit as st

from datetime import datetime, timedelta
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
        
class DateTimeInput(BaseModel):
    operation: str = Field(description="The date/time operation to perform (e.g., 'current_time', 'add_time')")
    date_str: Optional[str] = Field(default=None, description="The date string (e.g., '2025-01-26 14:30')")
    time_str: Optional[str] = Field(default=None, description="Time string to perform operations on (e.g., '14:30')")
    timezone: Optional[str] = Field(default="UTC", description="Timezone for the operation (e.g., 'UTC', 'US/Eastern')")
    time_to_add: Optional[str] = Field(default=None, description="Time duration to add/subtract (e.g., '10 minutes', '2 hours')")
    compare_time: Optional[str] = Field(default=None, description="Compare the given time to the current time (e.g., '14:30')")
    date_format: Optional[str] = Field(default="%Y-%m-%d %H:%M:%S", description="Date format for input and output")

class DateTimeTool(BaseTool):
    name: str = "date_time_tool"
    description: str = "Handles various date and time operations such as getting the current time, adding time, comparing times, and converting time zones."
    args_schema: Type[BaseModel] = DateTimeInput
    return_direct: bool = True

    def _run(
        self,
        operation: str,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
        timezone: Optional[str] = "UTC",
        time_to_add: Optional[str] = None,
        compare_time: Optional[str] = None,
        date_format: Optional[str] = "%Y-%m-%d %H:%M:%S",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)

            if operation == "current_time":
                # Get the current time in the specified timezone
                return {"result": current_time.strftime(date_format)}
            
            elif operation == "add_time" and time_str and time_to_add:
                # Add or subtract time from a given time string
                time_obj = datetime.strptime(time_str, "%H:%M")
                time_delta = self._parse_time_duration(time_to_add)
                new_time = time_obj + time_delta
                return {"result": new_time.strftime("%H:%M")}
            
            elif operation == "compare_time" and compare_time:
                # Compare given time with current time
                given_time = datetime.strptime(compare_time, "%H:%M")
                time_diff = given_time - current_time.replace(hour=given_time.hour, minute=given_time.minute, second=0, microsecond=0)
                return {"result": f"Time difference: {time_diff}"}

            elif operation == "format_schedule_time" and time_str:
                # Format given schedule time into a more readable format
                time_obj = datetime.strptime(time_str, "%H:%M")
                return {"result": f"Next bus/train at {time_obj.strftime('%I:%M %p')}"}

            else:
                return {"error": "Invalid operation or missing parameters"}
        except Exception as e:
            return {"error": str(e)}

    def _parse_time_duration(self, time_str: str) -> timedelta:
        """
        Parse time duration string into timedelta (e.g., '10 minutes' or '2 hours').
        """
        time_units = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        time_duration = 0
        for unit in time_units:
            if unit in time_str:
                num = int(time_str.split()[0])
                time_duration += num * time_units[unit]
        
        return timedelta(seconds=time_duration)

    async def _arun(
        self,
        operation: str,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
        timezone: Optional[str] = "UTC",
        time_to_add: Optional[str] = None,
        compare_time: Optional[str] = None,
        date_format: Optional[str] = "%Y-%m-%d %H:%M:%S",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Dict:
        # Implementing the async version of _run, which calls _run synchronously
        return self._run(operation, date_str, time_str, timezone, time_to_add, compare_time, date_format)

if __name__ == "__main__":
    tool = GTFSCoordinatorTool()
    response = tool._run(query="""Give me all unique short route names""")
    print(response)

