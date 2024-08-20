## Its working very much perfect for textual data and graphical data.

import os
import time
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

app = Flask(__name__)

# Upload a file with an "assistants" purpose
def upload_file(file_path):
    return client.files.create(file=open(file_path, "rb"), purpose='assistants')

# Create an assistant with specified instructions and tools
def create_assistant(instructions, file_id):
    return client.beta.assistants.create(
        instructions=instructions,
        name="RAG",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}],
        tool_resources={"code_interpreter": {"file_ids": [file_id]}}
    )

# Run the assistant and retrieve its response
def run_assistant(assistant_id, question):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=question
    )
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

    while run.status not in ["completed", "failed"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(10)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages

# Process a textual query and return the result
def process_textual_query(question):
    file = upload_file("data1/BrCA Dataset_N5030_lab.csv")
    assistant = create_assistant("You are a personal math tutor. When asked a math question, write and run code to answer the question.", file.id)
    messages = run_assistant(assistant.id, question)
    
    for message in messages.data:
        if message.role == 'assistant':
            return "\n".join([content_block.text.value for content_block in message.content])

    return "No valid response received."

# Process a graphical query and return the image file path
def process_graphical_query(question):
    file = upload_file("data1/BrCA Dataset_N5030_lab.csv")
    assistant = create_assistant("You are a personal data analyst. Generate a chart for the requested data.", file.id)
    messages = run_assistant(assistant.id, question)

    for message in messages.data:
        for content in message.content:
            if content.type == 'image_file':
                image_data = client.files.content(content.image_file.file_id)
                image_data_bytes = image_data.read()

                # Save image to static/images directory
                image_dir = "static/images"
                os.makedirs(image_dir, exist_ok=True)

                image_filename = f"{image_dir}/{content.image_file.file_id}.png"
                with open(image_filename, "wb") as file:
                    file.write(image_data_bytes)
                return image_filename

    return {"error": "No image generated"}

# Flask route to handle both textual and graphical queries
@app.route('/usa-health', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('query')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Determine whether to process as text or graphical
    if any(keyword in question.lower() for keyword in ["plot", "visual", "graph", "draw", "chart"]):
        image_filename = process_graphical_query(question)
        if isinstance(image_filename, dict) and "error" in image_filename:
            return jsonify({"error": image_filename["error"]}), 400

        return send_file(image_filename, mimetype='image/png')
    else:
        try:
            answer = process_textual_query(question)
            return jsonify({"answer": answer})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
