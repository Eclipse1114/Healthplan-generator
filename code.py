import streamlit as st
from google import genai
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Health & Well-Being Co-Pilot", 
    page_icon="➕", 
    layout="centered"
)

# Custom CSS for a clean Red-and-White EMS Theme
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #111111;
    }
    .stButton>button {
        background-color: #FFFFFF;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #B71C1C;
        color: white;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFAFA;
        border-right: 1px solid #FFCDD2;
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
