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
import hashlib
import shutil
import time
from openai import OpenAI
from streamlit_local_storage import LocalStorage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="ReceiptKeeper",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== POLISHED DARK STYLING (Improved + Uploader Fix) ======================
st.markdown("""
<style>
    /* Main background & text */
    .main {background-color: #0a0c12;}
    .stApp {background-color: #0a0c12; color: #e6e9f0;}
    
    /* Headings */
    h1 {color: #00e5ff; font-size: 2.9rem !important; font-weight: 700; margin-bottom: 0.1rem;}
    h2 {color: #00d4ff; font-weight: 600;}
    h3 {color: #7dd3fc; font-weight: 600;}
    
    /* Buttons */
    .stButton>button {
        background-color: #00b4d8;
        color: #ffffff;
        border-radius: 10px;
        font-weight: 700;
        height: 3.2em;
        box-shadow: 0 4px 12px rgba(0, 180, 216, 0.3);
    }
    .stButton>button:hover { 
        background-color: #00e5ff; 
        color: #0a0c12;
        box-shadow: 0 6px 16px rgba(0, 229, 255, 0.4);
    }
    
    /* File Uploader - Bright Red & Visible */
    .stFileUploader label {
        color: #ffffff !important;
        font-weight: 600;
    }
    .stFileUploader button {
        background-color: #00b4d8 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 2px solid #00e5ff;
    }
    .stFileUploader button:hover {
        background-color: #ff4d4d !important;
        color: #ffffff !important;
        border-color: #ff8080;
    }
    .stFileUploader div[role="button"] {
        color: #ff4d4d !important;   /* Bright red upload text */
        font-weight: 600;
    }
    
    /* Inputs & Selects */
    .stSelectbox, .stTextInput, .stNumberInput, .stTextArea, .stDateInput {
        border-radius: 10px;
    }
    
    /* Metrics - HIGH contrast */
    .stMetric {
        background-color: #161b26;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .stMetric label { color: #94a3b8; font-size: 0.95rem; }
    .stMetric [data-testid="stMetricValue"] {
        color: #67e8f9 !important;
        font-size: 1.85rem !important;
        font-weight: 700;
    }
    
    /* Dataframe */
    .stDataFrame {
        border-radius: 10px;
        border: 1px solid #334155;
    }
    
    /* Alerts */
    .stSuccess, .stInfo, .stWarning {
        border-radius: 10px;
        border-left: 5px solid #00b4d8;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #11151f;
    }
    
    p, li, span { color: #e2e8f0; line-height: 1.6; }
    strong, b { color: #67e8f9; }
</style>
""", unsafe_allow_html=True)

# ====================== CONFIG ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    except:
        pass

if not OPENAI_API_KEY:
    st.error("❌ OpenAI API key not found. Please set it in environment variables or .streamlit/secrets.toml")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ====================== PRIVATE KEY SYSTEM (Browser Remember + Reliable Logout) ======================
# Requires this line in requirements.txt:
# streamlit-local-storage==0.0.25

PRIVATE_KEY_STORAGE_NAME = "receiptkeeper_private_key"
browser_storage = LocalStorage()

# Server-side state lasts only for the current Streamlit browser session.
if "user_key" not in st.session_state:
    st.session_state.user_key = None

if "private_key_input" not in st.session_state:
    st.session_state.private_key_input = ""

if "remember_private_key" not in st.session_state:
    st.session_state.remember_private_key = True

# Prevent a stale browser-component result from logging the user straight back
# in immediately after they press Forget Key.
if "block_key_restore" not in st.session_state:
    st.session_state.block_key_restore = False

st.sidebar.markdown("# 🛡️ ReceiptKeeper")
st.sidebar.markdown("### 📄 Your Private Space")

# Only read browser storage when logout has not explicitly blocked restoration.
remembered_key = None
if not st.session_state.block_key_restore:
    remembered_key = browser_storage.getItem(PRIVATE_KEY_STORAGE_NAME)

# Automatically restore a genuinely remembered key.
if (
    remembered_key
    and not st.session_state.user_key
    and not st.session_state.block_key_restore
):
    restored_key = str(remembered_key).strip()
    if restored_key:
        st.session_state.user_key = restored_key
        st.session_state.private_key_input = restored_key
        st.session_state.remember_private_key = True

# Show entry controls only when no private space is active.
if not st.session_state.user_key:
    entered_key = st.sidebar.text_input(
        "Private Key",
        type="password",
        key="private_key_input",
        help=(
            "Choose something memorable. This separates your data from other "
            "private spaces."
        ),
    )

    remember_key = st.sidebar.checkbox(
        "Remember this key on this browser",
        key="remember_private_key",
        help=(
            "Use this only on your own trusted device. The browser will retain "
            "the key after the tab or browser is closed."
        ),
    )

    if st.sidebar.button(
        "🔓 Open Private Space",
        type="primary",
        use_container_width=True,
    ):
        cleaned_key = entered_key.strip()

        if not cleaned_key:
            st.sidebar.error("Enter a private key first.")
        else:
            st.session_state.user_key = cleaned_key
            st.session_state.block_key_restore = False

            if remember_key:
                browser_storage.setItem(
                    PRIVATE_KEY_STORAGE_NAME,
                    cleaned_key,
                )
                time.sleep(1.5)
                st.sidebar.success("Private key remembered on this browser.")
            else:
                # Remove any previously remembered browser key.
                browser_storage.deleteAll()
                time.sleep(1.5)
                st.sidebar.success("Private space opened for this session only.")

# Stop after rendering the local-storage component and login controls.
if not st.session_state.user_key:
    st.info("👆 Enter your private key in the sidebar to begin.")
    st.stop()

st.sidebar.success(
    f"✅ Private space active: {st.session_state.user_key[:8]}..."
)

# Reliable logout:
# 1. Delete browser local storage using the package's actual deletion method.
# 2. Block stale component values from restoring the old key.
# 3. Clear private-space session data.
# 4. Rerun back to the key-entry screen.
if st.sidebar.button(
    "🗑️ Forget Key on This Browser",
    use_container_width=True,
):
    browser_storage.deleteAll()
    time.sleep(2.0)

    st.session_state.user_key = None
    st.session_state.private_key_input = ""
    st.session_state.remember_private_key = False
    st.session_state.block_key_restore = True

    # Clear other page-specific values that may belong to the previous user.
    for state_key in list(st.session_state.keys()):
        if state_key not in {
            "user_key",
            "private_key_input",
            "remember_private_key",
            "block_key_restore",
        }:
            del st.session_state[state_key]

    st.rerun()

# ====================== DATABASE + PERSISTENT RECEIPT STORAGE ======================
safe_hash = hashlib.md5(st.session_state.user_key.encode()).hexdigest()[:12]

# Use Render's mounted persistent disk when available.
# On a local computer, keep the database and images beside the app.
if os.path.isdir("/data"):
    storage_root = "/data"
else:
    storage_root = os.path.abspath(".")

os.makedirs(storage_root, exist_ok=True)

db_name = os.path.join(storage_root, f"receipts_{safe_hash}.db")

# Every private key receives its own persistent receipt-image directory.
receipt_storage_dir = os.path.join(
    storage_root,
    "receipt_images",
    safe_hash,
)
os.makedirs(receipt_storage_dir, exist_ok=True)

conn = sqlite3.connect(db_name, check_same_thread=False)
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

# Best-effort migration for older receipts that were saved in the legacy
# relative "receipts/" folder. If an old file still exists, copy it into the
# persistent per-user directory and update the database path.
c.execute("""
    SELECT id, image_path
    FROM receipts
    WHERE image_path IS NOT NULL
      AND TRIM(image_path) != ''
""")

for receipt_id, old_image_path in c.fetchall():
    try:
        old_image_path = str(old_image_path).strip()

        # Already migrated and still available.
        if os.path.isfile(old_image_path):
            old_abs = os.path.abspath(old_image_path)
            target_root_abs = os.path.abspath(receipt_storage_dir)

            try:
                already_persistent = (
                    os.path.commonpath([old_abs, target_root_abs])
                    == target_root_abs
                )
            except ValueError:
                already_persistent = False

            if already_persistent:
                continue

            original_name = os.path.basename(old_abs)
            migrated_name = f"{receipt_id}_{original_name}"
            migrated_path = os.path.join(
                receipt_storage_dir,
                migrated_name,
            )

            if not os.path.exists(migrated_path):
                shutil.copy2(old_abs, migrated_path)

            c.execute(
                "UPDATE receipts SET image_path = ? WHERE id = ?",
                (migrated_path, receipt_id),
            )

    except Exception:
        # Migration must never stop the app from opening.
        pass

conn.commit()

# ====================== HEADER ======================
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("# 📄 ReceiptKeeper")
with col2:
    st.markdown("**Private • AI-Powered • One-time Purchase • Full Data Ownership**")

st.markdown("---")

# ====================== PWA SUPPORT ======================
st.markdown("""
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#00b4d8">
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }
    </script>
""", unsafe_allow_html=True)

# ====================== NAVIGATION ======================
page = st.sidebar.radio(
    "Navigation",
    ["Add Receipt", "Mileage Tracker", "My Receipts", "Monthly Report", "Tax Insights", "Gmail Sync"]
)

# (All the rest of your code remains unchanged from here down)
# ====================== HELPER FUNCTIONS ======================
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

    footer = "Original receipt images are stored with the user's ReceiptKeeper data. Generated by ReceiptKeeper."
    elements.append(Paragraph(footer, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray)))

    doc.build(elements)
    return filename


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

                os.makedirs(receipt_storage_dir, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                safe_name = "".join(
                    ch for ch in merchant
                    if ch.isalnum() or ch in (" ", "-", "_")
                ).strip().replace(" ", "_")
                safe_name = safe_name or "receipt"

                ext = (
                    uploaded_file.name.rsplit(".", 1)[-1].lower()
                    if "." in uploaded_file.name
                    else "jpg"
                )
                filename = f"{timestamp}_{safe_name}.{ext}"
                file_path = os.path.join(receipt_storage_dir, filename)

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

            image_path = str(selected.get("image_path") or "").strip()

            if image_path and os.path.isfile(image_path):
                file_extension = os.path.splitext(image_path)[1].lower()

                if file_extension == ".pdf":
                    with open(image_path, "rb") as original_pdf:
                        st.download_button(
                            "⬇️ Open / Download Original PDF Receipt",
                            data=original_pdf.read(),
                            file_name=os.path.basename(image_path),
                            mime="application/pdf",
                            use_container_width=True,
                        )
                else:
                    st.image(
                        image_path,
                        width=550,
                        caption="Original Receipt",
                    )
            elif image_path:
                st.error(
                    "The receipt data is safe, but this older original image "
                    "file is no longer available. It was probably saved before "
                    "persistent image storage was enabled."
                )
            else:
                st.info("No original image was attached to this receipt.")
    else:
        st.info("No receipts yet. Add your first receipt on the Add Receipt page.")

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
    st.info("This feature requires a one-time Google OAuth setup (credentials.json in the project folder).")

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
            st.info("Make sure you have 'credentials.json' in the same folder and have completed the OAuth flow once.")

# Show a one-time reset confirmation after Streamlit reruns.
if "reset_completed_message" in st.session_state:
    st.success(st.session_state.pop("reset_completed_message"))

# ====================== SIDEBAR TOOLS ======================
st.sidebar.markdown("---")
if st.sidebar.button("💾 One-Click Full Backup"):
    with st.spinner("Creating backup..."):
        backup_name = f"ReceiptKeeper_Backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        with zipfile.ZipFile(backup_name, "w") as zipf:
            if os.path.isdir(receipt_storage_dir):
                for root, _, files in os.walk(receipt_storage_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(
                            full_path,
                            receipt_storage_dir,
                        )
                        archive_path = os.path.join(
                            "receipt_images",
                            relative_path,
                        )
                        zipf.write(full_path, arcname=archive_path)

            if os.path.exists(db_name):
                zipf.write(
                    db_name,
                    arcname=os.path.basename(db_name),
                )
        with open(backup_name, "rb") as f:
            st.sidebar.download_button("⬇️ Download Backup", f, backup_name, mime="application/zip")
        st.sidebar.success("Backup created successfully!")

# Reset Everything (reliable, per-user safe)
with st.sidebar.expander("🔄 Reset Everything (Danger Zone)"):
    st.error(
        "⚠️ This permanently deletes every receipt and mileage record "
        "belonging to the currently active private key."
    )

    with st.form("reset_everything_form", clear_on_submit=False):
        reset_confirm = st.text_input(
            "Type exactly 'RESET' to confirm",
            key="reset_confirm",
        )
        reset_submitted = st.form_submit_button(
            "✅ Confirm Permanent Deletion",
            type="primary",
            use_container_width=True,
        )

    if reset_submitted:
        if reset_confirm != "RESET":
            st.error("Reset cancelled. Type exactly RESET.")
        else:
            try:
                # Collect only receipt files referenced by this key's database.
                c.execute("""
                    SELECT image_path
                    FROM receipts
                    WHERE image_path IS NOT NULL
                      AND TRIM(image_path) != ''
                """)
                user_image_paths = [
                    row[0] for row in c.fetchall()
                    if row and row[0]
                ]

                # Remove all records belonging to the active private key.
                c.execute("DELETE FROM receipts")
                conn.commit()

                # Reclaim unused SQLite space.
                c.execute("VACUUM")
                conn.commit()

                deleted_images = 0
                for image_path in user_image_paths:
                    try:
                        if os.path.isfile(image_path):
                            os.remove(image_path)
                            deleted_images += 1
                    except OSError:
                        # A missing or locked file must not stop the reset.
                        pass

                # Remove page values tied to the deleted records.
                for state_key in ["detected", "reset_confirm", "selected_id"]:
                    st.session_state.pop(state_key, None)

                st.session_state.reset_completed_message = (
                    f"✅ Reset complete. All records for this private key "
                    f"were deleted, together with {deleted_images} linked "
                    f"receipt image(s)."
                )
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Reset failed: {e}")

st.sidebar.info("✅ All data stored privately per key for tax compliance")

# ====================== FOOTER ======================
st.sidebar.markdown("---")
st.caption("ReceiptKeeper • Local-first + Hosted • Built for freelancers who value privacy")