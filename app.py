from flask import Flask
from discord import Webhook
import datetime
import requests
import redis
import json
import aiohttp
from dotenv import load_dotenv
load_dotenv()
import os


redis_client = redis.from_url(os.getenv("REDIS_URL"))
app = Flask(__name__)
app.config['DISCORD_URL'] = os.getenv("DISCORD_URL")
app.config['STRAVA_TOKEN'] = os.getenv("STRAVA_TOKEN")
app.config['STRAVA_API_URL'] = os.getenv("STRAVA_API_URL", "https://www.strava.com/api/v3")
app.config['STRAVA_AUTH_URL'] = os.getenv("STRAVA_AUTH_URL", "https://www.strava.com/api/v3/oauth/token")
app.config['STRAVA_TOKEN_EXPIRE'] = os.getenv("STRAVA_TOKEN_EXPIRE")
app.config['STRAVA_TOKEN_REFRESH'] = os.getenv("STRAVA_TOKEN_REFRESH")
app.config['STRAVA_CLIENT_ID'] = os.getenv("STRAVA_CLIENT_ID")
app.config['STRAVA_CLIENT_SECRET'] = os.getenv("STRAVA_CLIENT_SECRET")


async def send_message(data):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(app.config['DISCORD_URL'], session=session)
        await webhook.send(f"""
        Athlete: {data['athlete']['firstname']} {data['athlete']['lastname']}
        Distance:{data['distance']} m
        Time: {data['elapsed_time']} s
        Sport:{data['sport_type']}
        Elevation: {data['total_elevation_gain']} m
        """, username='Foo')

def fill_data():
    id = 1100162
    data = requests.get(
        f"{app.config['STRAVA_API_URL']}/clubs/{id}/activities",headers={"Authorization": f"Bearer {app.config['STRAVA_TOKEN']}"}
        ).json()
    for x in data:
        redis_client.lpush('CLUB_ACTIVITIES',json.dumps(x))
    redis_client.ltrim('CLUB_ACTIVITIES',0,29)

@app.route("/ping")
def ping():
    return "Pong"

@app.route("/")
async def index():
    print(app.config['STRAVA_TOKEN_EXPIRE'])
    if datetime.datetime.fromtimestamp(float(app.config['STRAVA_TOKEN_EXPIRE'])) > datetime.datetime.now():
        id = 1100162
        data = requests.get(
            f"{app.config['STRAVA_API_URL']}/clubs/{id}/activities",headers={"Authorization": f"Bearer {app.config['STRAVA_TOKEN']}"}
            ).json()

        club_activities = [json.loads(redis_client.lindex('CLUB_ACTIVITIES', x)) for x in range(redis_client.llen('CLUB_ACTIVITIES'))]
        new_activities = [x for x in data if x not in club_activities]
        if len(new_activities) == 0:
            for x in data:
                redis_client.lpush('CLUB_ACTIVITIES',json.dumps(x))
            redis_client.ltrim('CLUB_ACTIVITIES',0,29)
        else:
            for activity in new_activities:
                await send_message(activity)
    else:
        payload=f"client_id={app.config['STRAVA_CLIENT_ID']}&client_secret={app.config['STRAVA_CLIENT_SECRET']}&grant_type=refresh_token&refresh_token={app.config['STRAVA_TOKEN_REFRESH']}"
        headers = {
          'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", app.config['STRAVA_AUTH_URL'], headers=headers, data=payload).json()
        app.config['STRAVA_TOKEN']=response['access_token']
        app.config['STRAVA_TOKEN_REFRESH']=response['refresh_token']
        app.config['STRAVA_TOKEN_EXPIRE']=response['expires_at']
    return {'message':"Transaccion correcta"}

fill_data()
