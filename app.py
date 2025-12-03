import streamlit as st
from groq import Groq
from tavily import TavilyClient
from fpdf import FPDF

# 1. Setup
st.set_page_config(page_title="AI Fact Checker Pro", page_icon="🕵️")
st.title("🕵️ Instant Fact Checker Agent")

# 2. Get Keys
groq_key = st.secrets["GROQ_API_KEY"]
tavily_key = st.secrets["TAVILY_API_KEY"]

if not groq_key or not tavily_key:
    st.error("Missing API Keys! Please check your Secrets.")
    st.stop()

client = Groq(api_key=groq_key)
tavily = TavilyClient(api_key=tavily_key)

# --- PDF GENERATION FUNCTION ---
def create_pdf(query, ai_response, sources_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Fact Check Report", ln=True, align='C')
    pdf.ln(10)
    
    # Claim
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Claim Verified:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=query)
    pdf.ln(5)
    
    # Analysis
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="AI Analysis:", ln=True)
    pdf.set_font("Arial", size=11)
    # Clean text to remove emojis/unsupported chars for PDF
    clean_response = ai_response.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_response)
    pdf.ln(5)

    # Sources
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Sources Found:", ln=True)
    pdf.set_font("Arial", size=10)
    clean_sources = sources_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_sources)
    
    # Save to string/bytes
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP LOGIC ---
user_query = st.text_input("Enter a claim to verify:", placeholder="e.g., Apple released a foldable phone today")

if user_query:
    with st.spinner("🕵️‍♂️ Agent is gathering evidence..."):
        try:
            # 1. Search
            search_response = tavily.search(query=user_query, max_results=4)
            
            # Format results for the AI and for the PDF
            source_list = []
            for result in search_response['results']:
                source_list.append(f"- {result['title']} ({result['url']})")
            sources_text = "\n".join(source_list)
            
            context_data = "\n".join([f"{r['title']}: {r['content']}" for r in search_response['results']])

            # 2. Analyze
            prompt = f"""
            You are a Fact Checker. Verify this claim: "{user_query}"
            Using these search results:
            {context_data}
            
            Write a professional summary. 
            Start with "VERDICT: [TRUE / FALSE / UNVERIFIED]".
            Then explain the evidence.
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            
            final_answer = completion.choices[0].message.content
            
            # 3. Display Results
            st.success("Analysis Complete!")
            st.markdown(final_answer)
            st.markdown("---")
            st.subheader("Sources Used:")
            st.text(sources_text)
            
            # 4. Generate PDF Button
            pdf_bytes = create_pdf(user_query, final_answer, sources_text)
            
            st.download_button(
                label="📄 Download Professional Report (PDF)",
                data=pdf_bytes,
                file_name="fact_check_report.pdf",
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
