import io
import textwrap
import requests
from flask import Flask, request, jsonify, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

GEMINI_API_KEY = "AIzaSyD5g2rltvf4J3p5KavrvH07LjIm-RxoipY"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

LEGAL_KB = [
    {"title": "IPC 354", "content": "Assault on a woman intending to outrage modesty."},
    {"title": "IPC 354A", "content": "Sexual harassment including unwelcome contact, demands for sexual favours, obscene remarks."},
    {"title": "IPC 376", "content": "Rape and serious sexual assault, with strict punishment."},
    {"title": "IPC 379", "content": "Theft of movable property taken without consent."},
    {"title": "IPC 406", "content": "Criminal breach of trust, misusing property entrusted to a person."},
    {"title": "IPC 420", "content": "Cheating and dishonestly inducing delivery of property, common in frauds and scams."},
    {"title": "IPC 498A", "content": "Cruelty by husband or his relatives, including dowry harassment."},
    {"title": "IPC 509", "content": "Words, gestures or acts intended to insult the modesty of a woman."},
    {"title": "IT Act 66C/66D", "content": "Cyber identity theft and cheating by impersonation using computer resources."},
    {"title": "Helplines", "content": "112 Emergency, 100 Police, 108 Ambulance, 1091 Women, 1098 Childline, 1930 Cyber fraud."},
    {"title": "Legal Notice Format", "content": "Legal notice: sender address, receiver address, facts in order, relevant IPC/sections, demands, time to comply, warning of legal action, signature."}
]

def retrieve_context(query):
    query = query.lower()

    ipc_keywords = {
        "IPC 354": ["touch", "molest", "outrage modesty", "physical harassment", "inappropriate", "body touching"],
        "IPC 354A": ["sexual", "harass", "harassment", "sexual comments", "demand favours", "unwelcome", "online harassment"],
        "IPC 354D": ["stalk", "stalking", "follow", "spy", "tracking", "cyberstalking"],
        "IPC 376": ["rape", "sexual assault", "forced", "sexual violence", "intercourse", "sexual abuse"],
        "IPC 509": ["insult", "modesty", "abuse", "verbal", "comments", "instagram", "whatsapp", "message", "voice", "video"],
        "IPC 498A": ["husband", "domestic", "dowry", "cruelty", "marriage", "family abuse"],
        "IPC 420": ["fraud", "scam", "cheat", "money", "bank", "loan", "fake", "payment", "job offer"],
        "IPC 406": ["trust", "property misuse", "asset", "documents", "embezzle"],
        "IPC 379": ["steal", "theft", "stolen", "lost mobile", "robbery"],
        "IPC 506": ["threat", "blackmail", "fear", "intimidate", "criminal intimidation"],
        "IT Act 66C/66D": ["cyber", "impersonation", "identity", "fake account", "online cheating", "hacked"]
    }

    matched_sections = []

    for section, keywords in ipc_keywords.items():
        if any(word in query for word in keywords):
            for doc in LEGAL_KB:
                if doc["title"].lower() == section.lower():
                    matched_sections.append(f"{doc['title']} – {doc['content']}")

    if not matched_sections:
        matched_sections = [
            "IPC 509 – Words, gestures, or electronic communication intended to insult the modesty of a woman.",
            "IPC 354 – Assault or criminal force to a woman intending to outrage her modesty.",
            "IPC 506 – Criminal intimidation using threats, blackmail, or fear."
        ]

    return "\n".join(matched_sections)



def build_local_notice_and_summary(user_query):
    context = retrieve_context(user_query)
    tokens = [t.lower() for t in user_query.split() if len(t) > 2]
    
    matched_ipc = []
    for doc in LEGAL_KB:
        if "ipc" in doc["title"].lower() or "it act" in doc["title"].lower():
            text = (doc["title"] + " " + doc["content"]).lower()
            if any(t in text for t in tokens):
                matched_ipc.append(doc)

    if not matched_ipc:
        matched_ipc = [d for d in LEGAL_KB if d["title"].startswith("IPC")][:3]

    ipc_lines = [d["title"] + " – " + d["content"] for d in matched_ipc]

    notice_lines = [
        "To,",
        "The Concerned Authority,",
        "Address: ____________",
        "",
        "Subject: Legal notice regarding grievance and request for appropriate action",
        "",
        "Respected Sir/Madam,",
        "",
        "I, ____________, residing at ____________________, wish to bring to your notice the following facts:",
        "",
        "1. " + user_query.strip(),
        "2. The above incident has caused me mental distress, inconvenience, and loss.",
    ]

    if ipc_lines:
        notice_lines.append("")
        notice_lines.append("Based on initial understanding, the following legal provisions may be applicable:")
        for line in ipc_lines:
            notice_lines.append("• " + line)

    notice_lines.extend([
        "",
        "You are requested to take appropriate action within 15 days from receiving this notice, "
        "failing which I shall be compelled to pursue legal remedies as per law.",
        "",
        "This notice is issued without prejudice to any other legal rights and remedies available to me under the law.",
        "",
        "Place: ____________",
        "Date: ____________",
        "Signature: ____________"
    ])

    notice_text = "\n".join(notice_lines)

    summary_parts = [
        "Based on your statement, the following legal sections may be relevant:",
    ]
    summary_parts.extend(["• " + line for line in ipc_lines])

    summary_parts.extend([
        "",
        "Important helplines in India:",
        "• 100 – Police",
        "• 1091 – Women Helpline",
        "• 1930 – Cyber Crime / Online Fraud",
        "• 112 – National Emergency",
        "",
        "Disclaimer: This response is based on general legal information. "
        "For exact legal guidance, please consult a qualified lawyer or legal authority.",
    ])

    summary_text = "\n".join(summary_parts)

    full_reply = (
        "Here is your drafted legal notice based on the information provided:\n\n"
        "---LEGAL_NOTICE_START---\n"
        + notice_text +
        "\n---LEGAL_NOTICE_END---\n\n"
        "---SUMMARY_START---\n"
        + summary_text +
        "\n---SUMMARY_END---"
    )

    return full_reply, notice_text


def call_gemini_with_rag(user_query):
    try:
        
        wants_notice = any(word in user_query.lower() for word in [
            "legal notice", "draft notice", "make notice", "generate notice", "create notice"
        ])

        if not wants_notice:
       
            prompt = f"""
You are LegalBot, a friendly Indian legal assistant.
Talk like a human, not a robot.
First respond normally with empathy, then explain relevant IPC sections
in simple words, and then ask the user if they want a legal notice.

USER MESSAGE:
{user_query}

RELATED IPC INFO:
{retrieve_context(user_query)}

RESPONSE STRUCTURE:
1️⃣ Empathetic and friendly reply  
2️⃣ Explain possible IPC sections in simple words  
3️⃣ Guide what action they can take (police/cyber cell/evidence)  
4️⃣ Ask: "Would you like me to help you draft a legal notice?"  
⚠️ Do NOT generate notice unless user asks specifically.
"""
            response = requests.post(
                GEMINI_API_URL,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            data = response.json()
            if response.status_code != 200 or "error" in data:
                raise Exception("gemini_failed")
            text = data["candidates"][0]["content"]["parts"][0].get("text", "")
            return text, ""  # No notice yet

        else:
        
            full_reply, notice = build_local_notice_and_summary(user_query)
            return full_reply, notice

    except Exception:
        relevant_sections = retrieve_context(user_query)

        fallback = (
            "💛 I'm really sorry you are going through this. I understand how stressful this can be.\n\n"
            "📘 Based on what you shared, here are some *possibly relevant legal sections*:\n"
            f"{relevant_sections}\n\n"
            "📝 To guide you better, could you please share a little more?\n"
            "• When did this happen?\n"
            "• Was it online (Instagram, WhatsApp, email, call) or in person?\n"
            "• Do you have screenshots, chats, or any proof?\n\n"
            "📌 You can also report cyber cases at the official portal: cybercrime.gov.in\n"
            "📞 Useful Helplines: 1930 Cyber Fraud | 1091 Women | 112 Emergency\n\n"
            "If you'd like, I can help you **draft a legal notice or cyber complaint format** — just type: draft notice"
        )
        return fallback, ""

        


def create_pdf_from_text(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica", 11)
    width, height = A4
    y = height - 50
    for paragraph in text.split("\n"):
        for line in textwrap.wrap(paragraph, width=95):
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = height - 50
            pdf.drawString(40, y, line)
            y -= 15
        y -= 8
    pdf.save()
    buffer.seek(0)
    return buffer
@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    data = request.get_json(force=True)
    text = (data.get("legal_notice") or "").strip()

    if not text:
        return jsonify({"error": "No notice text provided"}), 400

    pdf_buf = create_pdf_from_text(text)
    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="legal_notice.pdf"
    )


@app.route("/")
def index():
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LegalBot – Indian Law AI Assistant</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:linear-gradient(135deg,#0f172a,#312e81,#7c3aed);
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:24px;
}
.shell{
  width:100%;
  max-width:960px;
  background:rgba(15,23,42,0.96);
  border-radius:24px;
  box-shadow:0 22px 70px rgba(0,0,0,0.75);
  overflow:hidden;
  border:1px solid rgba(148,163,184,0.6);
}
.header{
  padding:16px 22px;
  text-align:center;
  background:linear-gradient(90deg,#f97316,#ec4899,#6366f1);
  color:white;
}
.header h1{
  font-size:1.4rem;
}
.header p{
  font-size:0.8rem;
  margin-top:4px;
}
.main{
  padding:16px 18px 14px;
}
#messages{
  height:430px;
  overflow-y:auto;
  padding:10px;
  background:radial-gradient(circle at top left,rgba(56,189,248,0.22),rgba(15,23,42,1));
  border-radius:16px;
}
.msg{
  max-width:78%;
  padding:9px 12px;
  border-radius:14px;
  margin-bottom:10px;
  font-size:0.88rem;
  line-height:1.4;
  white-space:pre-wrap;
}
.user{
  margin-left:auto;
  background:linear-gradient(135deg,#22c55e,#16a34a);
  color:white;
  border-bottom-right-radius:4px;
}
.bot{
  margin-right:auto;
  background:rgba(148,163,184,0.22);
  color:#e5e7eb;
  border-bottom-left-radius:4px;
}
.input-row{
  margin-top:12px;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
textarea{
  flex:1;
  border-radius:14px;
  border:1px solid rgba(75,85,99,0.9);
  background:#020617;
  color:#e5e7eb;
  padding:9px 11px;
  font-size:0.86rem;
  resize:vertical;
  min-height:52px;
  max-height:130px;
}
textarea:focus{
  outline:2px solid #22c55e;
  outline-offset:1px;
}
.send-btn{
  border:none;
  width:44px;
  height:44px;
  border-radius:50%;
  background:linear-gradient(135deg,#22c55e,#22c1c3);
  display:flex;
  align-items:center;
  justify-content:center;
  cursor:pointer;
  font-size:1.2rem;
  color:white;
  box-shadow:0 7px 18px rgba(34,197,94,0.7);
}
#pdfBtn{
  margin-top:8px;
  border:none;
  padding:7px 14px;
  border-radius:999px;
  background:linear-gradient(135deg,#facc15,#f97316);
  color:#111827;
  font-size:0.78rem;
  font-weight:600;
  cursor:pointer;
  display:none;
}
.status{
  margin-top:6px;
  font-size:0.74rem;
  color:#9ca3af;
}
</style>
</head>
<body>
<div class="shell">
  <div class="header">
    <h1>⚖️ LegalBot – Indian Law AI Assistant</h1>
    <p>Describe your situation. I will respond kindly, suggest IPC sections, draft a sample notice, and list helplines. Not a lawyer.</p>
  </div>
  <div class="main">
    <div id="messages"></div>
    <div class="input-row">
      <textarea id="userInput" placeholder="Example: I transferred money for a job offer and they blocked me. What can I do?"></textarea>
      <button class="send-btn" id="sendBtn">➤</button>
    </div>
    <button id="pdfBtn">📄 Download Legal Notice PDF</button>
    <div class="status" id="status">Press Enter or ➤ to send.</div>
  </div>
</div>
<script>
let lastNotice="";

function addMessage(text,isUser){
  const box=document.getElementById("messages");
  const div=document.createElement("div");
  div.className="msg " + (isUser?"user":"bot");
  div.textContent=text;
  box.appendChild(div);
  box.scrollTop=box.scrollHeight;
}

async function sendMessage(){
  const input=document.getElementById("userInput");
  const text=input.value.trim();
  if(!text) return;
  addMessage(text,true);
  input.value="";
  lastNotice="";
  document.getElementById("pdfBtn").style.display="none";
  document.getElementById("status").textContent="LegalBot is thinking...";
  try{
    const res=await fetch("/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:text})
    });
    const data=await res.json();
    addMessage(data.reply || "(empty reply)",false);
    if(data.legal_notice){
      lastNotice=data.legal_notice;
      document.getElementById("pdfBtn").style.display="inline-block";
      document.getElementById("status").textContent="Notice ready. You can download the PDF.";
    }else{
      document.getElementById("status").textContent="You can ask another question.";
    }
  }catch(e){
    addMessage("Network error: "+e,false);
    document.getElementById("status").textContent="Network error.";
  }
}

async function downloadPDF(){
  if(!lastNotice) return;
  document.getElementById("status").textContent="Creating PDF notice...";
  const res=await fetch("/generate_pdf",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({legal_notice:lastNotice})
  });
  const blob=await res.blob();
  const url=window.URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download="legal_notice.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  document.getElementById("status").textContent="PDF downloaded.";
}

document.getElementById("sendBtn").addEventListener("click",sendMessage);
document.getElementById("userInput").addEventListener("keydown",function(e){
  if(e.key==="Enter" && !e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
});
document.getElementById("pdfBtn").addEventListener("click",downloadPDF);
</script>
</body>
</html>
    '''
    return render_template_string(html)

from flask import session
app.secret_key = "legal-bot-secret"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    msg = (data.get("message") or "").strip().lower()

    if not msg:
        return jsonify({"reply": "Please describe your situation so I can help.", "legal_notice": ""})

    if msg in ["restart", "hi", "hello", "start", "hey"]:
        session.clear()
        session["stage"] = "ask_incident"
        return jsonify({"reply": 
            "💬 I'm here to help. Please briefly describe what happened.\n"
            "(Example: Someone stalked me, cyber bullying, emotional abuse, money fraud)",
            "legal_notice": ""
        })

    if "stage" not in session:
        session["stage"] = "ask_incident"
        return jsonify({"reply": 
            "💬 Please describe what happened (e.g., stalking, scam, harassment).",
            "legal_notice": ""
        })

    if session["stage"] == "ask_incident":
        session["incident"] = msg
        ipc_info = retrieve_context(msg)
        session["stage"] = "offer_notice"
        return jsonify({"reply": 
            f"💛 Thank you for sharing.\n\n📘 Based on your situation, these IPC sections may apply:\n\n{ipc_info}\n\n"
            "Would you like me to draft a legal notice or complaint?\n👉 Type: yes, draft notice",
            "legal_notice": ""
        })

    if session["stage"] == "offer_notice" and ("yes" in msg or "notice" in msg or "draft" in msg):
        full_reply, notice = build_local_notice_and_summary(session["incident"])
        session["stage"] = "done"
        return jsonify({"reply": full_reply, "legal_notice": notice})

    reply, notice = call_gemini_with_rag(msg)
    return jsonify({"reply": reply, "legal_notice": notice})

if __name__ == "__main__":
    print("Open in browser: http://127.0.0.1:5000")
    app.run(debug=True)
