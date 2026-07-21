import streamlit as st
import pandas as pd
from PIL import Image
import sqlite3
import datetime
import os
import io
import base64
import zipfile
import json
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER

# ====================== SETUP INSTRUCTIONS ======================
# 1. Create folder .streamlit → secrets.toml with: OPENAI_API_KEY = "sk-..."
# 2. For Gmail: place credentials.json in this folder

# ====================== CONFIG ======================
import os
import streamlit as st

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    try:
        if st.secrets and "OPENAI_API_KEY" in st.secrets:
            OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        OPENAI_API_KEY = None

if not OPENAI_API_KEY:
    st.error("❌ OpenAI API key not found.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

conn = sqlite3.connect('receipts.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS receipts
             (id INTEGER PRIMARY KEY,
              date TEXT,
              merchant TEXT,
              amount REAL,
              expense_type TEXT,
              receipt_type TEXT,
              category TEXT,
              project TEXT,
              notes TEXT,
              image_path TEXT,
              created_at TEXT)''')
conn.commit()

st.set_page_config(page_title="ReceiptKeeper", layout="wide")

# ====================== PWA SUPPORT ======================
st.markdown("""
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e3a5f">
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }
    </script>
""", unsafe_allow_html=True)

# ====================== CUSTOM STYLING ======================
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #1e3a5f;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton>button:hover { background-color: #2c5282; }
    .stSelectbox, .stTextInput, .stNumberInput, .stTextArea { border-radius: 8px; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #1e3a5f; }
    .stSuccess { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ ReceiptKeeper")
st.caption("Smart Receipt Tracking for Freelancers • Full Data Ownership • No Subscriptions")

# ====================== ONBOARDING ======================
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

if not st.session_state.onboarded:
    st.balloons()
    st.success("🎉 Welcome to ReceiptKeeper!")
    st.info("""
    **Built for freelancers & solo users who want:**
    - Full ownership of their data  
    - Original receipt images for tax proof  
    - No monthly subscriptions  
    - Smart project tracking + accountant-ready reports
    """)
    if st.button("Got it, let's get started!"):
        st.session_state.onboarded = True
        st.rerun()

page = st.sidebar.radio("Navigation", ["Add Receipt", "Mileage Tracker", "My Receipts", "Monthly Report", "Tax Insights", "Gmail Sync"])

# ====================== PDF GENERATOR ======================
def generate_accountant_pdf(df, year=None, filename="ReceiptKeeper_Accountant_Report.pdf"):
    if year is None:
        year = datetime.datetime.now().year
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER, spaceAfter=12)
    elements.append(Paragraph(f"ReceiptKeeper - Accountant Report {year}", title_style))
    elements.append(Spacer(1, 15))

    total = df['amount'].sum()
    count = len(df)
    summary_data = [
        ['Total Expenses', f'R {total:,.2f}'],
        ['Receipts', str(count)],
        ['Period', f'Jan - Dec {year}'],
        ['Generated', datetime.datetime.now().strftime('%Y-%m-%d')],
    ]
    summary_table = Table(summary_data, colWidths=[9*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.12, 0.23, 0.37)),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    if 'category' in df.columns:
        cat_sum = df.groupby('category')['amount'].sum().sort_values(ascending=False)
        cat_data = [['Category', 'Amount']]
        for cat, amt in cat_sum.items():
            cat_data.append([cat, f'R {amt:,.2f}'])
        cat_table = Table(cat_data, colWidths=[9*cm, 6*cm])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.12, 0.23, 0.37)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        elements.append(Paragraph("Spending by Category", styles['Heading3']))
        elements.append(cat_table)
        elements.append(Spacer(1, 20))

    elements.append(Paragraph("All Receipts", styles['Heading3']))
    table_data = [['Date', 'Merchant', 'Amount', 'Category', 'Project', 'Notes']]
    for _, row in df.iterrows():
        table_data.append([
            str(row.get('date', ''))[:10],
            str(row.get('merchant', ''))[:45],
            f"R{row.get('amount', 0):,.2f}",
            str(row.get('category', '')),
            str(row.get('project', ''))[:30],
            str(row.get('notes', ''))[:60]
        ])
    col_widths = [2.*cm, 5.*cm, 2.*cm, 2.5*cm, 3.*cm, 5*cm]
    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.12, 0.23, 0.37)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 15))

    footer = "Original receipt images are stored locally in the 'receipts' folder. Generated by ReceiptKeeper."
    elements.append(Paragraph(footer, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray)))

    doc.build(elements)
    return filename

# ====================== DUPLICATE DETECTION ======================
def is_duplicate(merchant, amount, date_str):
    c.execute("""
        SELECT id FROM receipts
        WHERE LOWER(merchant) = LOWER(?)
        AND ABS(amount - ?) < 2
        AND date = ?
    """, (merchant, amount, date_str))
    return c.fetchone() is not None

# ====================== ADD RECEIPT ======================
if page == "Add Receipt":
    st.header("📥 Add New Receipt")

    col1, col2 = st.columns(2)
    with col1:
        expense_type = st.selectbox("Expense Type", ["Business", "Private"])
    with col2:
        receipt_type = st.selectbox("Receipt Type", ["Paper / Photo Receipt", "Digital Receipt (Uber, Email, PDF)", "Crypto Transaction"])

    uploaded_file = st.file_uploader("Upload receipt photo or PDF", type=['png', 'jpg', 'jpeg', 'pdf'])

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        if uploaded_file.type != "application/pdf":
            st.image(image_bytes, width=450, caption="Uploaded Receipt")

        if st.button("🔍 Read Receipt with AI", type="primary"):
            with st.spinner("AI is reading your receipt..."):
                base64_image = base64.b64encode(image_bytes).decode('utf-8')

                prompt = """Extract the following from this receipt image and return ONLY valid JSON:
{
  "merchant": "Merchant name",
  "amount": 123.45,
  "date": "YYYY-MM-DD"
}"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    response_format={"type": "json_object"},
                    max_tokens=300
                )

                result = response.choices[0].message.content

                try:
                    data = json.loads(result)
                    merchant = data.get("merchant", "Unknown").strip()
                    amount = float(data.get("amount", 0))
                    date_str = data.get("date", str(datetime.date.today()))

                    try:
                        parsed_date = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                    except:
                        parsed_date = datetime.date.today()

                    st.session_state.detected = {
                        "merchant": merchant,
                        "amount": amount,
                        "date": parsed_date,
                        "summary": f"**Detected:** {merchant} — R{amount:,.2f} on {parsed_date}"
                    }
                    st.success("AI Analysis Complete!")
                except Exception as e:
                    st.error(f"Failed to parse AI response: {e}")
                    st.session_state.detected = {
                        "merchant": "Unknown",
                        "amount": 0.0,
                        "date": datetime.date.today(),
                        "summary": "⚠️ AI could not parse clearly. Please check and edit manually."
                    }

        if "detected" in st.session_state:
            d = st.session_state.detected
            st.markdown(d["summary"], unsafe_allow_html=True)

            merchant = st.text_input("Merchant", value=d["merchant"])
            amount = st.number_input("Amount (R)", value=d["amount"], step=0.01)
            date = st.date_input("Date", value=d["date"])

            colA, colB = st.columns(2)
            with colA:
                category = st.selectbox("Category", ["Food", "Transport", "Crypto", "Shopping", "Fees", "Software", "Other"])
            with colB:
                project = st.text_input("Project / Client (optional)")

            notes = st.text_area("Notes (optional)")

            if st.button("💾 Save Receipt", type="primary"):
                if is_duplicate(merchant, amount, str(date)):
                    st.warning("⚠️ A very similar receipt already exists.")
                    if not st.checkbox("Save anyway"):
                        st.stop()

                os.makedirs("receipts", exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in merchant if c.isalnum() or c in (' ', '-', '_')).strip().replace(" ", "_")
                ext = uploaded_file.name.split(".")[-1] if "." in uploaded_file.name else "jpg"
                filename = f"{timestamp}_{safe_name}.{ext}"
                file_path = f"receipts/{filename}"

                with open(file_path, "wb") as f:
                    f.write(image_bytes)

                created_at = datetime.datetime.now().isoformat()

                c.execute("""INSERT INTO receipts
                             (date, merchant, amount, expense_type, receipt_type, category, project, notes, image_path, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (str(date), merchant, amount, expense_type, receipt_type, category, project, notes, file_path, created_at))
                conn.commit()

                st.success("✅ Receipt saved successfully!")
                st.balloons()
                if "detected" in st.session_state:
                    del st.session_state.detected

# ====================== MILEAGE TRACKER ======================
elif page == "Mileage Tracker":
    st.header("🚗 Mileage Tracker")
    st.caption("Log business travel for tax deductions")

    date = st.date_input("Date", datetime.date.today())
    project = st.text_input("Project / Client")
    start = st.text_input("Starting Location")
    end = st.text_input("Ending Location")
    distance = st.number_input("Distance (km)", min_value=0.0, step=0.1)
    rate = st.number_input("Rate per km", value=4.0, step=0.1)
    notes = st.text_area("Purpose / Notes")

    if st.button("Save Mileage"):
        amount = distance * rate
        c.execute("""INSERT INTO receipts
                     (date, merchant, amount, expense_type, receipt_type, category, project, notes, image_path, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (str(date), f"Mileage: {start} to {end}", amount, "Business", "Mileage", "Transport", project, notes, "", datetime.datetime.now().isoformat()))
        conn.commit()
        st.success(f"✅ Mileage saved! Deduction ≈ R{amount:,.2f}")
        st.balloons()

# ====================== MY RECEIPTS ======================
elif page == "My Receipts":
    st.header("📋 My Receipts")
    df = pd.read_sql_query("SELECT * FROM receipts ORDER BY date DESC", conn)

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input("🔍 Smart Search")
        with col2:
            cat_filter = st.selectbox("Category", ["All"] + sorted(df["category"].dropna().unique().tolist()))
        with col3:
            proj_filter = st.selectbox("Project/Client", ["All"] + sorted([p for p in df["project"].dropna().unique().tolist() if p]))

        filtered = df.copy()
        if search:
            filtered = filtered[filtered.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]
        if proj_filter != "All":
            filtered = filtered[filtered["project"] == proj_filter]

        st.dataframe(filtered[["id", "date", "merchant", "amount", "category", "project"]], use_container_width=True, hide_index=True)

        st.subheader("View Receipt Image")
        if not filtered.empty:
            selected_id = st.selectbox("Select ID", filtered["id"].tolist())
            selected = df[df["id"] == selected_id].iloc[0]
            st.write(f"**{selected['merchant']}** — R{selected['amount']:.2f}")
            if os.path.exists(selected['image_path']):
                st.image(selected['image_path'], width=550, caption="Original Receipt")
    else:
        st.info("No receipts yet.")

# ====================== MONTHLY REPORT ======================
elif page == "Monthly Report":
    st.header("📊 Monthly & Year-to-Date Report")
    df = pd.read_sql_query("SELECT * FROM receipts", conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        today = datetime.date.today()
        current_year = today.year

        ytd = df[df['date'].dt.year == current_year]
        st.subheader(f"Year-to-Date {current_year}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("YTD Total", f"R{ytd['amount'].sum():,.2f}")
        with col2:
            st.metric("YTD Receipts", len(ytd))

        current_month = today.strftime('%Y-%m')
        current_month_df = df[df['date'].dt.strftime('%Y-%m') == current_month]
        st.subheader(f"Current Month ({current_month})")
        st.metric("This Month Total", f"R{current_month_df['amount'].sum():,.2f}")

        if st.button("📄 Generate Full Year Accountant PDF", type="primary"):
            with st.spinner("Creating PDF..."):
                pdf_path = generate_accountant_pdf(df, current_year)
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ Download PDF", f, pdf_path, mime="application/pdf")
                st.success("PDF ready!")

# ====================== TAX INSIGHTS ======================
elif page == "Tax Insights":
    st.header("💰 Tax Insights")
    df = pd.read_sql_query("SELECT * FROM receipts", conn)
    if not df.empty:
        business = df[df['expense_type'] == 'Business']
        if not business.empty:
            st.metric("Total Business Expenses", f"R{business['amount'].sum():,.2f}")
            meals = business[business['category'] == 'Food']['amount'].sum()
            st.write(f"Meals (50% deductible estimate): **R{meals * 0.5:,.2f}**")

# ====================== GMAIL SYNC ======================
elif page == "Gmail Sync":
    st.header("📧 Gmail Sync")
    st.caption("Scan your Gmail for receipts and import them automatically")
    st.info("This feature requires a one-time Google OAuth setup (credentials.json).")

    if st.button("🔄 Scan Gmail for Receipts"):
        try:
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import pickle

            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            service = build('gmail', 'v1', credentials=creds)

            results = service.users().messages().list(userId='me', q='receipt OR invoice OR payment', maxResults=20).execute()
            messages = results.get('messages', [])

            imported = 0
            for msg in messages:
                msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = msg_data.get('payload', {})
                headers = payload.get('headers', [])
               
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')

                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                            break

                prompt = f"""Extract merchant, amount, and date from this email. Return JSON:
{{"merchant": "...", "amount": 0.0, "date": "YYYY-MM-DD"}}
Email Subject: {subject}
From: {sender}
Body: {body[:2000]}"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)

                if data.get("merchant") and data.get("amount"):
                    c.execute("""INSERT INTO receipts
                                 (date, merchant, amount, expense_type, receipt_type, category, project, notes, image_path, created_at)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                              (data.get("date", str(datetime.date.today())),
                               data.get("merchant"),
                               float(data.get("amount", 0)),
                               "Business", "Digital Receipt (Uber, Email, PDF)",
                               "Other", "", f"Imported from Gmail: {subject}", "", datetime.datetime.now().isoformat()))
                    conn.commit()
                    imported += 1

            st.success(f"✅ Imported {imported} receipts from Gmail!")
        except Exception as e:
            st.error(f"Gmail sync failed: {e}")
            st.info("Make sure you have 'credentials.json' in the same folder.")

# ====================== SIDEBAR BACKUP ======================
st.sidebar.markdown("---")
if st.sidebar.button("💾 One-Click Full Backup"):
    with st.spinner("Creating backup..."):
        backup_name = f"ReceiptKeeper_Backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        with zipfile.ZipFile(backup_name, 'w') as zipf:
            if os.path.exists("receipts"):
                for root, _, files in os.walk("receipts"):
                    for file in files:
                        zipf.write(os.path.join(root, file))
            if os.path.exists("receipts.db"):
                zipf.write("receipts.db")
        with open(backup_name, "rb") as f:
            st.sidebar.download_button("⬇️ Download Backup", f, backup_name)
        st.sidebar.success("Backup created!")

st.sidebar.info("✅ All data stored locally for tax compliance")