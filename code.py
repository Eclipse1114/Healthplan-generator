import streamlit as st
from google import genai
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Health & Well-Being Co-Pilot", 
    page_icon="➕", 
    layout="centered"
)

# Custom CSS for a dark, warm, textured White-and-Red Theme
st.markdown(
    """
    <style>
    /* Global App Background & Main Text */
    .stApp {
        background-color: #121212 !important;
        color: #FFFFFF !important;
    }

    /* Form Container */
    div[data-testid="stForm"] {
        background-color: #1A1A1A !important;
        border: 1px solid #331A1A !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }

    /* Target Labels Above Text Areas and Inputs */
    div[data-testid="stForm"] label,
    div[data-testid="stForm"] label p,
    div[data-testid="stForm"] label span {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }

    /* Text Area Input Box & Text */
    div[data-testid="stTextArea"] textarea {
        background-color: #262626 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }

    /* Placeholder Text inside Text Area */
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #999999 !important;
        opacity: 1 !important;
    }

    /* File Uploader Container & Inner Box */
    div[data-testid="stFileUploader"] {
        background-color: transparent !important;
    }

    div[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploader"] section {
        background-color: #262626 !important;
        border: 1px dashed #D32F2F !important;
        border-radius: 8px !important;
    }

    /* File Uploader "200MB per file" Subtext */
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] p,
    div[data-testid="stFileUploader"] span {
        color: #DDDDDD !important;
    }

    /* Upload Button Styling */
    div[data-testid="stFileUploader"] button {
        background-color: #D32F2F !important;
        border: none !important;
        border-radius: 8px !important;
    }

    /* Upload Button Text & Icon */
    div[data-testid="stFileUploader"] button *,
    div[data-testid="stFileUploader"] button p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    div[data-testid="stFileUploader"] button:hover {
        background-color: #F44336 !important;
    }

    /* Submit Button ("Generate Care Plan") */
    .stButton > button {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(211, 47, 47, 0.3) !important;
    }

    .stButton > button:hover {
        background-color: #F44336 !important;
        color: #FFFFFF !important;
    }

    /* Chat Input Styling */
    [data-testid="stChatInput"] textarea {
        color: #FFFFFF !important;
        background-color: #1E1E1E !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# App Header
st.title("➕ Health & Well-Being Co-Pilot")
st.markdown(
    "A practical decision-support tool for frontline workers and caregivers. "
    "Type out notes, symptoms, or drop in a photo to map out the best immediate and ongoing steps."
)
st.divider()

# Initialize Gemini Client safely
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Missing API Key. Please add your `GEMINI_API_KEY` to Streamlit secrets.")
    st.stop()

# Initialize session state for conversation history and keeping the plan persistent
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "plan_generated" not in st.session_state:
    st.session_state.plan_generated = False

# User Input Form
with st.form("health_form"):
    st.subheader("Case Notes & Details")
    
    user_context = st.text_area(
        "What's happening? Include physical, mental, or situational context:",
        placeholder="e.g., Client took a hard fall earlier, complains of a dull headache, and is acting unusually confused and irritable...",
        height=135
    )
    
    uploaded_file = st.file_uploader(
        "Upload an image (optional — e.g., injury photo, physical documentation, or notes):",
        type=["jpg", "jpeg", "png"]
    )
    
    submitted = st.form_submit_button("Generate Care Plan", type="primary")

# Processing Initial Input
if submitted:
    if not user_context.strip() and not uploaded_file:
        st.warning("Please add some notes or upload an image first.")
    else:
        with st.spinner("Reviewing details and pulling together a plan..."):
            try:
                system_instruction = (
                    "You are an experienced clinical co-pilot assisting health and support workers. "
                    "Your job is to help structure safe, comprehensive care pathways that cover physical, "
                    "neurological, and mental health factors equally. Prioritize safety, practical pacing, "
                    "and clear escalation red flags."
                )
                
                prompt = f"""
                Review the following case details and any attached media to generate a clear, grounded care plan.
                
                Organize your response into these exact sections using markdown:
                - **Immediate Actions:** What needs to be handled right now to ensure safety.
                - **Care & Recovery Steps:** Practical interventions covering physical, mental, or neurological angles.
                - **Routine & Pacing:** Recommended daily rhythms, rest, or monitoring guidelines.
                - **Red Flags to Watch:** Warning signs that mean it's time for immediate emergency medical care.

                Keep the tone professional, steady, and empathetic. Conclude with a clear safety disclaimer.
                
                Case Context: {user_context}
                """
                
                contents = [prompt]
                if uploaded_file is not None:
                    image = Image.open(uploaded_file)
                    contents.append(image)
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                    )
                )
                
                # CLEAR old history/plan when a new plan is requested
                st.session_state.chat_history = []
                
                # Store interaction in session state chat history
                user_display = f"**Case Context:** {user_context}" if user_context.strip() else "**Case Context:** [Attached Media]"
                st.session_state.chat_history.append({"role": "user", "text": user_display})
                st.session_state.chat_history.append({"role": "model", "text": response.text})
                st.session_state.plan_generated = True
                
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# Render entire chat history consistently
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

# Post-generation options and follow-up interaction loop
if st.session_state.plan_generated:
    # Grab the latest model response for the download button
    latest_plan = [m["text"] for m in st.session_state.chat_history if m["role"] == "model"]
    if latest_plan:
        st.download_button(
            label="📥 Download Care Plan (.txt)",
            data=latest_plan[-1],
            file_name="care_plan_notes.txt",
            mime="text/plain"
        )
    
    st.info(
        "💡 **Note:** This tool is designed to support clinical judgment, "
        "not to replace professional diagnosis or emergency medical care."
    )

    # Follow-up chat input box
    if user_question := st.chat_input("Ask a follow-up question about the plan (e.g., de-escalation tips, alternative actions)..."):
        # 1. Append and render user message immediately
        st.session_state.chat_history.append({"role": "user", "text": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
            
        # 2. Generate and render model response
        with st.spinner("Thinking..."):
            try:
                context = "\n".join([f"{m['role']}: {m['text']}" for m in st.session_state.chat_history])
                
                followup_prompt = f"""You are an experienced clinical co-pilot continuing this consultation:
{context}

Answer the user's latest question concisely while keeping the same professional, safe, and empathetic tone."""
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=followup_prompt,
                )
                
                reply = response.text
                st.session_state.chat_history.append({"role": "model", "text": reply})
                with st.chat_message("model"):
                    st.markdown(reply)
                    
            except Exception as e:
                st.error(f"Something went wrong: {e}")
