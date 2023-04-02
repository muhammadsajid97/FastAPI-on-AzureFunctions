import logging
import azure.functions as func
from FastAPIApp import app  # Main API application
import random
import openai
from googletrans import Translator
import geocoder
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import json
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

port = os.environ["PORT"]
openai.api_key = os.environ["OPENAI_API_KEY"]
CONNECTION_STRING = os.environ["SERVICE_BUS_CONNECTION_STRING"]
QUEUE_NAME = os.environ["CONVERSATION_HISTORY_QUEUE_NAME"]
APPINSIGHTS_INSTRUMENTATIONKEY = os.environ["APPINSIGHTS_INSTRUMENTATIONKEY"]

# port = 8000
# openai.api_key = "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"
# CONNECTION_STRING = "Endpoint=sb://hey-alli.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=/SWAb7hn6MXVqkjcAd+4IbI1lSCgoKorI+ASbIfB4+E="
# QUEUE_NAME = "create_brain_conversation_history"
# APPINSIGHTS_INSTRUMENTATIONKEY = "6266c10c-7cb6-4116-a110-68162029450b"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(AzureLogHandler(
    connection_string=f'InstrumentationKey={APPINSIGHTS_INSTRUMENTATIONKEY}'))

service_bus_client = ServiceBusClient.from_connection_string(CONNECTION_STRING)
queue_sender = service_bus_client.get_queue_sender(QUEUE_NAME)


class TranslationInput(BaseModel):
    text: str
    from_lang: str
    to_lang: str


class QuestionInput(BaseModel):
    question: str


class ConversationHitoryInput(BaseModel):
    message: str


@app.get("/ping")
async def ping():
    return {"Hey. Brain is up and running....!!!"}


@app.get("/greeting")
async def greeting():
    Greetings = [
        "Hey there!",
        "Hello! How can I assist you?",
        "Hello! How can I help you?",
        "nods",
        "You are talking to HeyALLI",
        "Welcome to HeyAlli",
        "I am glad you are talking to me! My name is HeyAlli",
        "How can I help?"
    ]
    return {"message": random.choice(Greetings)}


@app.post("/question")
async def heyalli(input_data: QuestionInput):
    def HeyALLI(prompt, max_tokens=500):
        completions = openai.Completion.create(
            engine="text-davinci-002", prompt=prompt, max_tokens=max_tokens)
        return completions.choices[0].text.strip()

    if input_data.question == "I am Bryan":
        return {"response": "Welcome Bryan! How can I assist you?"}
    if "your" in input_data.question and "name" in input_data.question:
        return {"response": "I am Alli."}
    if not input_data.question:
        return {"response": "I am sorry, you didn't enter any question!"}

    response = HeyALLI(input_data.question)

    if len(response) == 0:
        return {"response": "I am sorry, I didn't get any response. Please try again!"}

    await create_conversation_history("question", input_data.question, response)
    logger.info(
        f"Brain => Question: {input_data.question}, Response: {response}")
    return {"response": response}


@app.post("/translate")
async def translate(input_data: TranslationInput):
    def TranslateFunc(text, from_lang, to_lang):
        translator = Translator()
        translation = translator.translate(text, src=from_lang, dest=to_lang)
        return translation.text

    translated_text = TranslateFunc(
        input_data.text, input_data.from_lang, input_data.to_lang)

    await create_conversation_history("translate", input_data.text, translated_text)
    return {"translated_text": translated_text}


async def create_conversation_history(input_type: str, input_data: str, message: str):
    try:
        message = message.replace('"', '')
        doc = {
            "date_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "user_location": await get_location_info(),
            "type": input_type,
            "question": input_data,
            "message": message,
        }
        queue_sender.send_messages(ServiceBusMessage(json.dumps(doc)))
    except Exception as e:
        logger.exception(
            f"Brain fails: Failed to create conversation history: {e}")



@app.get("/location")
async def get_location_info():
    def get_location():
        location = geocoder.ip('me')
        country = location.country
        return country

    location_info = get_location()
    return {"location_info": location_info}


async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)
