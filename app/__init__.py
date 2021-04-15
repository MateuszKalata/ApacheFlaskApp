from flask import Flask
import redis

app = Flask(__name__)
db = redis.Redis(host="localhost", port=6379, decode_responses=True ,encoding="utf-8")
log = app.logger
# app.config.from_object('config')
from app import routes

