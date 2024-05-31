import streamlit as st
from openai import OpenAI
from io import StringIO
import os

st.title("SmyleGPT")


# Place an empty container for text responses before the input field

def saveFileOpenAI(location):
    #Create OpenAI Client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    #Send File to OpenAI
    file = client.files.create(file=open(location, "rb"),purpose='assistants')

    # Delete the temporary file
    os.remove(location)

    #Return FileID
    return file.id



client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

assistant = client.beta.assistants.create(
    instructions="Your are a AI model for Smyle, a LifeOS software designed to help people improve themselves",
    name="SmyleGPT",
    tools=[{"type": "file_search"}, {"type": "code_interpreter"}],
    model="gpt-3.5-turbo-0125"
)

assistant_id = assistant.id

# Initiate file uploader
uploaded_files = st.file_uploader("Upload Files for the Assistant", accept_multiple_files=True, key="uploader")
file_locations = []
yesfiles = False
# Setup text input and submit button within a form
with st.form(key='input_form', clear_on_submit=True):
    prompt = st.text_input("Enter your message here...", key='chat_input')
    submit_button = st.form_submit_button(label='Send')

if uploaded_files:
    yesfiles = True
    for uploaded_file in uploaded_files:
        # Read file as bytes
        bytes_data = uploaded_file.getvalue()
        location = f"temp_file_{uploaded_file.name}"
        # Save each file with a unique name
        with open(location, "wb") as f:
            f.write(bytes_data)
        file_locations.append(location)
        st.success(f'File {uploaded_file.name} has been uploaded successfully. Responses will now be focused on this document. Remove the document from the Upload Area to revert SmyleGPT to original status.')

    file_ids = [saveFileOpenAI(location) for location in file_locations]
    vector_store = client.beta.vector_stores.create(name="SmyleGPT",file_ids=file_ids)
    tool_resources = {"file_search": {"vector_store_ids": [vector_store.id]}}

    updated_assistant = client.beta.assistants.update(
        assistant_id,
        tool_resources=tool_resources
        )
    assistant_id =  updated_assistant.id
    vector_id = vector_store.id

if st.button("Clear Chat"):
        st.session_state.messages = []  # Clear the chat history
        st.session_state.thread_id = None

if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-3.5-turbo-0125"

if "messages" not in st.session_state:
        st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    elif message["role"] == "assistant":
        st.markdown(f"**SmyleGPT**: {message['content']}")

if submit_button and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    input = st.chat_message("User")
    input.write(prompt)
    res_container = st.empty()
    report = []
    if yesfiles:
        tool_resources = {"file_search": {"vector_store_ids": [vector_id]}}
        stream = client.beta.threads.create_and_run(
        tool_resources=tool_resources,
        assistant_id=assistant.id,
        thread={
            "messages": [
            {"role": "user", "content": prompt}
            ]
        },
        stream=True
    )
    else:
        stream = client.beta.threads.create_and_run(
        assistant_id=assistant.id,
        thread={
            "messages": [
            {"role": "user", "content": prompt}
            ]
        },
        stream=True
    )
    for event in stream:
        if event.data.object == "thread.message.delta":
            for content in event.data.delta.content:
                if content.type == 'text':
                    report.append(content.text.value)
                    #print(content.text.value)
                    result = "".join(report).strip()
                    # Update the middle container with the results
                    res_container.markdown(f"**SmyleGPT**: {result}")
                    
    st.session_state.messages.append({"role": "assistant", "content": result})