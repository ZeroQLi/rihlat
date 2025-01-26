# Rihlat - رحلة
## An AI voice assistant that tells you when the next bus is
#### project submission for the 42 Abu dhabi x Sambanova agentic AI hackathon

Rihlat is an AI voice assistant that specializes in answering queries regarding public transport (bus, metro, tram, etc). Features of rihlat include but are not limited to
- Querying and displaying route and bus information.
- fetching realtime arrival/departures times.
- Calculating transfers between a single or multiple stops.

The MVP for this project is a streamlit app. The agents are built on Sambanova's audio and text models and use Elevenlab's API to provide text to speech for our assistant
## Future Enhancements
- Realtime bus information using GTFS realtime
- Map and route vector tiles for visual output
- Accesibility and QOL features

## MVP SETUP
1.  Clone the repository
   ```
git clone https://github.com/ZeroQLi/rihlat.git
```
2.  create a python virutal enviroment
   ```
python -m venv venv
source ./venv/bin/activate
```
3. install all the required pacakages using ``pip``
```
pip install -r requirements.txt
```
4. create a ``~/.streamlit/secrets.toml`` file and add the following API keys
```
SAMBANOVA_API_KEY = "YOUR_API_KEY"
TOMTOM_API_KEY = "YOUR_API_KEY"
BINGMAPS_KEY = "YOUR_API_KEY"
ELEVENLABS_KEY = "YOUR_API_KEY"
```

5. Run the streamlit app
```
streamlit run app.py
```
