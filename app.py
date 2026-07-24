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
import uuid
import urllib.parse
import urllib.request
import urllib.error
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
    
    /* =========================================================
       HIGH-CONTRAST FORM CONTROLS
       Keep the application dark, but make every editable control
       light and readable. These selectors cover current Streamlit
       text, number, date, select and textarea components.
       ========================================================= */

    /* Widget labels */
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stDateInput label,
    .stSelectbox label {
        color: #f8fafc !important;
        font-weight: 650 !important;
    }

    /* Text, password, number and date inputs */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        caret-color: #0891b2 !important;
        border: 1px solid #64748b !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
    }

    /* Multi-line notes fields */
    [data-testid="stTextArea"] textarea {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        caret-color: #0891b2 !important;
        border: 1px solid #64748b !important;
        border-radius: 10px !important;
        min-height: 120px !important;
        line-height: 1.45 !important;
        font-weight: 500 !important;
        resize: vertical !important;
    }

    /* Placeholder text */
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stNumberInput"] input::placeholder,
    [data-testid="stDateInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }

    /* Select boxes */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        border: 1px solid #64748b !important;
        border-radius: 10px !important;
    }

    [data-testid="stSelectbox"] div[data-baseweb="select"] span,
    [data-testid="stSelectbox"] div[data-baseweb="select"] input,
    [data-testid="stSelectbox"] svg {
        color: #0f172a !important;
        fill: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* Select dropdown menu */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: #f8fafc !important;
    }

    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li {
        color: #0f172a !important;
        background-color: #f8fafc !important;
    }

    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] li:hover {
        background-color: #cffafe !important;
        color: #083344 !important;
    }

    /* Input focus ring */
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.24) !important;
        outline: none !important;
    }

    /* Buttons generated inside forms */
    .stFormSubmitButton > button {
        background-color: #00b4d8;
        color: #ffffff;
        border-radius: 10px;
        font-weight: 700;
        min-height: 3.2em;
        border: none;
    }

    /* Dedicated, highly visible private-space heading */
    .rk-private-space-title {
        color: #ffffff !important;
        background: linear-gradient(
            135deg,
            rgba(0, 180, 216, 0.22),
            rgba(0, 229, 255, 0.08)
        );
        border: 1px solid #0891b2;
        border-left: 5px solid #22d3ee;
        border-radius: 10px;
        padding: 0.72rem 0.85rem;
        margin: 0.35rem 0 0.85rem 0;
        font-size: 1.05rem;
        font-weight: 750;
        letter-spacing: 0.01em;
    }
    
    /* =========================================================
       DOWNLOAD BUTTONS
       Streamlit download buttons use a separate component from
       normal st.button controls, so they need their own styling.
       ========================================================= */
    [data-testid="stDownloadButton"] > button,
    .stDownloadButton > button {
        background-color: #075985 !important;
        color: #ffffff !important;
        border: 2px solid #22d3ee !important;
        border-radius: 10px !important;
        font-weight: 750 !important;
        min-height: 3.15em !important;
        box-shadow: 0 4px 12px rgba(8, 145, 178, 0.28) !important;
    }

    [data-testid="stDownloadButton"] > button p,
    [data-testid="stDownloadButton"] > button span,
    [data-testid="stDownloadButton"] > button div,
    .stDownloadButton > button p,
    .stDownloadButton > button span,
    .stDownloadButton > button div {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 750 !important;
    }

    [data-testid="stDownloadButton"] > button:hover,
    .stDownloadButton > button:hover {
        background-color: #22d3ee !important;
        color: #082f49 !important;
        border-color: #67e8f9 !important;
        box-shadow: 0 6px 16px rgba(34, 211, 238, 0.35) !important;
    }

    [data-testid="stDownloadButton"] > button:hover p,
    [data-testid="stDownloadButton"] > button:hover span,
    [data-testid="stDownloadButton"] > button:hover div,
    .stDownloadButton > button:hover p,
    .stDownloadButton > button:hover span,
    .stDownloadButton > button:hover div {
        color: #082f49 !important;
        -webkit-text-fill-color: #082f49 !important;
    }

    /* Dedicated ReceiptKeeper sidebar brand */
    .rk-sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        width: 100%;
        box-sizing: border-box;
        background: linear-gradient(
            135deg,
            #083344 0%,
            #0e7490 58%,
            #0891b2 100%
        );
        border: 1px solid #67e8f9;
        border-radius: 14px;
        padding: 0.85rem 0.9rem;
        margin: 0.1rem 0 0.7rem 0;
        box-shadow: 0 6px 18px rgba(8, 145, 178, 0.24);
    }

    .rk-sidebar-brand-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.15rem;
        height: 2.15rem;
        flex: 0 0 2.15rem;
        border-radius: 10px;
        background-color: #ecfeff;
        color: #0e7490 !important;
        font-size: 1.28rem;
        line-height: 1;
    }

    .rk-sidebar-brand-name {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-size: 1.33rem;
        line-height: 1.1;
        font-weight: 850;
        letter-spacing: -0.02em;
        white-space: nowrap;
    }

    .rk-sidebar-brand-name .rk-accent {
        color: #a5f3fc !important;
        -webkit-text-fill-color: #a5f3fc !important;
    }

    /* =========================================================
       LEMON SQUEEZY LICENCE GATE
       ========================================================= */
    .rk-license-shell {
        max-width: 760px;
        margin: 1.5rem auto 0 auto;
        background: linear-gradient(
            145deg,
            rgba(8, 51, 68, 0.94),
            rgba(15, 23, 42, 0.97)
        );
        border: 1px solid #0e7490;
        border-top: 4px solid #22d3ee;
        border-radius: 18px;
        padding: 1.4rem 1.55rem;
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.34);
    }

    .rk-license-kicker {
        color: #67e8f9 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.35rem;
    }

    .rk-license-title {
        color: #ffffff !important;
        font-size: 2rem;
        line-height: 1.15;
        font-weight: 850;
        margin-bottom: 0.55rem;
    }

    .rk-license-copy {
        color: #cbd5e1 !important;
        font-size: 1rem;
        line-height: 1.65;
    }

    .rk-license-points {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem 0.85rem;
        margin-top: 1rem;
    }

    .rk-license-point {
        color: #e2e8f0 !important;
        background-color: rgba(15, 118, 144, 0.16);
        border: 1px solid rgba(34, 211, 238, 0.25);
        border-radius: 10px;
        padding: 0.65rem 0.75rem;
        font-size: 0.92rem;
        font-weight: 650;
    }

    .rk-license-sidebar {
        color: #ffffff !important;
        background-color: rgba(14, 116, 144, 0.18);
        border: 1px solid #0e7490;
        border-radius: 10px;
        padding: 0.65rem 0.75rem;
        margin: 0.45rem 0 0.75rem 0;
        font-size: 0.89rem;
        line-height: 1.45;
    }

    .rk-license-sidebar strong {
        color: #a5f3fc !important;
    }

    @media (max-width: 700px) {
        .rk-license-points {
            grid-template-columns: 1fr;
        }
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

# ====================== LEMON SQUEEZY LICENCE + PRIVATE SPACE ======================
# Lemon Squeezy's License API does not require a seller API key for
# activate/validate/deactivate calls. The customer licence key is the credential.

LICENSE_STORAGE_NAME = "receiptkeeper_license_activation_v1"
PRIVATE_KEY_STORAGE_NAME = "receiptkeeper_private_key"

LEMON_LICENSE_API_BASE = "https://api.lemonsqueezy.com/v1/licenses"
EXPECTED_PRODUCT_NAME = os.getenv(
    "LEMONSQUEEZY_PRODUCT_NAME",
    "ReceiptKeeper Lifetime Access",
).strip()

# Optional strict identifiers. Add these Render environment variables once known.
# When present, v7 verifies them in addition to the exact product name.
EXPECTED_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "").strip()
EXPECTED_PRODUCT_ID = os.getenv("LEMONSQUEEZY_PRODUCT_ID", "").strip()
EXPECTED_VARIANT_ID = os.getenv("LEMONSQUEEZY_VARIANT_ID", "").strip()

# If Lemon Squeezy is temporarily unreachable, a recently validated browser
# activation may continue for this grace period.
LICENSE_OFFLINE_GRACE_HOURS = 72

browser_storage = LocalStorage()


def _normalise_id(value):
    """Return an API ID as a comparable string."""
    if value is None:
        return ""
    return str(value).strip()


def _normalise_email(value):
    return str(value or "").strip().casefold()


def _parse_browser_json(raw_value, storage_name):
    """Handle strings or wrapped dictionary values returned by the component."""
    if raw_value is None:
        return None

    value = raw_value

    if isinstance(value, dict) and storage_name in value:
        value = value.get(storage_name)

    # Some component versions can return an already decoded dictionary.
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()
    if not value or value.lower() in {"none", "null"}:
        return None

    # Decode up to twice to tolerate a JSON string stored inside JSON.
    for _ in range(2):
        try:
            decoded = json.loads(value)
        except Exception:
            break

        if isinstance(decoded, dict):
            return decoded

        if isinstance(decoded, str):
            value = decoded.strip()
            continue

        break

    return None


def _license_api_post(action, fields, timeout=18):
    """POST form data to Lemon Squeezy's public License API."""
    url = f"{LEMON_LICENSE_API_BASE}/{action}"
    encoded = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ReceiptKeeper/7.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            message = payload.get("error") or body
        except Exception:
            message = body or str(exc)

        raise RuntimeError(
            f"Lemon Squeezy rejected the request: {message}"
        ) from exc

    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise ConnectionError(
            f"Could not reach Lemon Squeezy: {reason}"
        ) from exc

    except TimeoutError as exc:
        raise ConnectionError(
            "The Lemon Squeezy request timed out."
        ) from exc


def _check_receiptkeeper_meta(meta, entered_email=None):
    """
    Fail closed when a licence belongs to another product, store, variant,
    or purchaser email.
    """
    meta = meta or {}

    product_name = str(meta.get("product_name") or "").strip()
    if product_name != EXPECTED_PRODUCT_NAME:
        return False, (
            "This licence belongs to a different product "
            f"({product_name or 'unknown product'})."
        )

    if EXPECTED_STORE_ID and (
        _normalise_id(meta.get("store_id")) != EXPECTED_STORE_ID
    ):
        return False, "This licence was issued by a different store."

    if EXPECTED_PRODUCT_ID and (
        _normalise_id(meta.get("product_id")) != EXPECTED_PRODUCT_ID
    ):
        return False, "This licence belongs to a different product ID."

    if EXPECTED_VARIANT_ID and (
        _normalise_id(meta.get("variant_id")) != EXPECTED_VARIANT_ID
    ):
        return False, "This licence belongs to a different product variant."

    if entered_email:
        purchase_email = _normalise_email(meta.get("customer_email"))
        if purchase_email != _normalise_email(entered_email):
            return False, (
                "The email address does not match the email used for "
                "this Lemon Squeezy purchase."
            )

    return True, ""


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _within_offline_grace(last_validated_utc):
    if not last_validated_utc:
        return False

    try:
        validated_at = datetime.datetime.fromisoformat(
            str(last_validated_utc).replace("Z", "+00:00")
        )
        if validated_at.tzinfo is None:
            validated_at = validated_at.replace(
                tzinfo=datetime.timezone.utc
            )

        age = (
            datetime.datetime.now(datetime.timezone.utc) - validated_at
        )
        return age.total_seconds() <= LICENSE_OFFLINE_GRACE_HOURS * 3600

    except Exception:
        return False


def _save_license_to_browser(payload):
    browser_storage.setItem(
        LICENSE_STORAGE_NAME,
        json.dumps(payload),
    )
    time.sleep(1.5)


def _clear_all_browser_storage():
    browser_storage.deleteAll()
    time.sleep(1.8)


def _restore_license_after_storage_clear():
    """
    The local-storage package exposes reliable deleteAll(), not a dependable
    per-key removal call. After clearing a private key, re-save the paid
    licence activation so the user is not forced to reactivate the software.
    """
    payload = st.session_state.get("license_storage_payload")
    if payload:
        _save_license_to_browser(payload)


# Initialise licence session state.
if "license_authorized" not in st.session_state:
    st.session_state.license_authorized = False

if "license_storage_payload" not in st.session_state:
    st.session_state.license_storage_payload = None

if "license_restore_checked" not in st.session_state:
    st.session_state.license_restore_checked = False

if "license_warning" not in st.session_state:
    st.session_state.license_warning = None


# Shared ReceiptKeeper sidebar brand.
st.sidebar.markdown(
    """
    <div class="rk-sidebar-brand">
        <div class="rk-sidebar-brand-icon">📄</div>
        <div class="rk-sidebar-brand-name">
            Receipt<span class="rk-accent">Keeper</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Read and validate a remembered browser activation once per Streamlit session.
if (
    not st.session_state.license_authorized
    and not st.session_state.license_restore_checked
):
    remembered_license_raw = browser_storage.getItem(LICENSE_STORAGE_NAME)
    remembered_license = _parse_browser_json(
        remembered_license_raw,
        LICENSE_STORAGE_NAME,
    )

    if remembered_license:
        remembered_key = str(
            remembered_license.get("license_key") or ""
        ).strip()
        remembered_instance = str(
            remembered_license.get("instance_id") or ""
        ).strip()
        remembered_email = str(
            remembered_license.get("customer_email") or ""
        ).strip()

        if remembered_key and remembered_instance:
            try:
                validation = _license_api_post(
                    "validate",
                    {
                        "license_key": remembered_key,
                        "instance_id": remembered_instance,
                    },
                )

                meta_ok, meta_error = _check_receiptkeeper_meta(
                    validation.get("meta"),
                    remembered_email,
                )

                status = str(
                    (validation.get("license_key") or {}).get("status")
                    or ""
                ).lower()

                if (
                    validation.get("valid") is True
                    and meta_ok
                    and status == "active"
                ):
                    remembered_license["last_validated_utc"] = _utc_now_iso()
                    remembered_license["status"] = status
                    remembered_license["meta"] = validation.get("meta") or {}
                    st.session_state.license_storage_payload = (
                        remembered_license
                    )
                    st.session_state.license_authorized = True
                    _save_license_to_browser(remembered_license)
                else:
                    st.session_state.license_warning = (
                        meta_error
                        or validation.get("error")
                        or "The remembered licence is no longer valid."
                    )

            except ConnectionError:
                # Avoid locking a paid user out during a short external outage.
                if _within_offline_grace(
                    remembered_license.get("last_validated_utc")
                ):
                    st.session_state.license_storage_payload = (
                        remembered_license
                    )
                    st.session_state.license_authorized = True
                    st.session_state.license_warning = (
                        "Lemon Squeezy could not be reached. ReceiptKeeper "
                        "is using the recently validated 72-hour offline grace."
                    )
                else:
                    st.session_state.license_warning = (
                        "ReceiptKeeper could not verify the remembered licence. "
                        "Check the internet connection and try again."
                    )

            except Exception as exc:
                st.session_state.license_warning = str(exc)

    st.session_state.license_restore_checked = True


# First-time licence activation screen.
if not st.session_state.license_authorized:
    st.markdown(
        """
        <div class="rk-license-shell">
            <div class="rk-license-kicker">Lifetime software access</div>
            <div class="rk-license-title">Activate ReceiptKeeper</div>
            <div class="rk-license-copy">
                Enter the email used during checkout and the licence key from
                your Lemon Squeezy receipt. Activation is required once on
                each authorised browser.
            </div>
            <div class="rk-license-points">
                <div class="rk-license-point">✓ One-time R800 purchase</div>
                <div class="rk-license-point">✓ Two browser activations</div>
                <div class="rk-license-point">✓ Original receipt storage</div>
                <div class="rk-license-point">✓ Lifetime licence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.license_warning:
        st.warning(st.session_state.license_warning)

    # Supports a future Lemon Squeezy redirect URL using:
    # ?license_key=[license_key]
    query_license = ""
    try:
        query_license = str(
            st.query_params.get("license_key", "") or ""
        ).strip()
    except Exception:
        query_license = ""

    with st.form("receiptkeeper_license_activation_form"):
        purchase_email = st.text_input(
            "Purchase email",
            placeholder="The email used at Lemon Squeezy checkout",
        )
        entered_license_key = st.text_input(
            "ReceiptKeeper licence key",
            value=query_license,
            type="password",
            placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        )
        activate_submitted = st.form_submit_button(
            "🔐 Activate ReceiptKeeper",
            type="primary",
            use_container_width=True,
        )

    st.caption(
        "Your licence activation is remembered only in this browser. "
        "Your separate private-space key controls which receipt records open."
    )

    if activate_submitted:
        cleaned_email = purchase_email.strip()
        cleaned_license_key = entered_license_key.strip()

        if not cleaned_email or "@" not in cleaned_email:
            st.error("Enter the email address used for the purchase.")
            st.stop()

        if not cleaned_license_key:
            st.error("Enter the licence key from your receipt.")
            st.stop()

        try:
            with st.spinner("Checking and activating your licence..."):
                # Validate the key and purchaser before consuming an activation.
                preflight = _license_api_post(
                    "validate",
                    {"license_key": cleaned_license_key},
                )

                preflight_ok, preflight_error = _check_receiptkeeper_meta(
                    preflight.get("meta"),
                    cleaned_email,
                )

                preflight_status = str(
                    (preflight.get("license_key") or {}).get("status")
                    or ""
                ).lower()

                if preflight.get("valid") is not True:
                    raise RuntimeError(
                        preflight.get("error")
                        or "This licence key is not valid."
                    )

                if not preflight_ok:
                    raise RuntimeError(preflight_error)

                if preflight_status in {"expired", "disabled"}:
                    raise RuntimeError(
                        f"This licence is {preflight_status}."
                    )

                browser_label = (
                    "ReceiptKeeper Browser "
                    + uuid.uuid4().hex[:10].upper()
                )

                activation = _license_api_post(
                    "activate",
                    {
                        "license_key": cleaned_license_key,
                        "instance_name": browser_label,
                    },
                )

                if activation.get("activated") is not True:
                    raise RuntimeError(
                        activation.get("error")
                        or "The licence could not be activated."
                    )

                activation_ok, activation_error = (
                    _check_receiptkeeper_meta(
                        activation.get("meta"),
                        cleaned_email,
                    )
                )
                if not activation_ok:
                    # Do not leave a wrong-product activation consuming a slot.
                    instance_id = str(
                        (activation.get("instance") or {}).get("id")
                        or ""
                    ).strip()
                    if instance_id:
                        try:
                            _license_api_post(
                                "deactivate",
                                {
                                    "license_key": cleaned_license_key,
                                    "instance_id": instance_id,
                                },
                            )
                        except Exception:
                            pass
                    raise RuntimeError(activation_error)

                instance = activation.get("instance") or {}
                instance_id = str(instance.get("id") or "").strip()
                if not instance_id:
                    raise RuntimeError(
                        "Lemon Squeezy did not return an activation instance."
                    )

                meta = activation.get("meta") or {}
                licence_payload = {
                    "license_key": cleaned_license_key,
                    "instance_id": instance_id,
                    "instance_name": str(instance.get("name") or browser_label),
                    "customer_email": str(
                        meta.get("customer_email") or cleaned_email
                    ).strip(),
                    "customer_name": str(
                        meta.get("customer_name") or ""
                    ).strip(),
                    "store_id": _normalise_id(meta.get("store_id")),
                    "product_id": _normalise_id(meta.get("product_id")),
                    "variant_id": _normalise_id(meta.get("variant_id")),
                    "product_name": str(
                        meta.get("product_name") or EXPECTED_PRODUCT_NAME
                    ).strip(),
                    "variant_name": str(
                        meta.get("variant_name") or ""
                    ).strip(),
                    "status": str(
                        (activation.get("license_key") or {}).get("status")
                        or "active"
                    ).lower(),
                    "last_validated_utc": _utc_now_iso(),
                }

                st.session_state.license_storage_payload = licence_payload
                st.session_state.license_authorized = True
                st.session_state.license_restore_checked = True
                st.session_state.license_warning = None

                _save_license_to_browser(licence_payload)

            st.success("✅ ReceiptKeeper licence activated.")
            st.rerun()

        except Exception as exc:
            st.error(f"Activation failed: {exc}")

    st.stop()


# Licensed-user sidebar.
license_payload = st.session_state.license_storage_payload or {}
licensed_email = str(
    license_payload.get("customer_email") or "Licensed customer"
)
st.sidebar.markdown(
    f"""
    <div class="rk-license-sidebar">
        <strong>✅ ReceiptKeeper licensed</strong><br>
        {licensed_email}
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.license_warning:
    st.sidebar.warning(st.session_state.license_warning)


# Allow a buyer to release this activation slot from the current browser.
with st.sidebar.expander("Licence settings"):
    st.caption(
        "Deactivate this browser before moving ReceiptKeeper to another device."
    )

    if st.button(
        "Deactivate Licence on This Browser",
        use_container_width=True,
        key="deactivate_receiptkeeper_license",
    ):
        current_payload = st.session_state.get(
            "license_storage_payload"
        ) or {}

        current_key = str(
            current_payload.get("license_key") or ""
        ).strip()
        current_instance = str(
            current_payload.get("instance_id") or ""
        ).strip()

        try:
            if current_key and current_instance:
                response = _license_api_post(
                    "deactivate",
                    {
                        "license_key": current_key,
                        "instance_id": current_instance,
                    },
                )
                if response.get("deactivated") is not True:
                    raise RuntimeError(
                        response.get("error")
                        or "The activation could not be deactivated."
                    )

            _clear_all_browser_storage()
            st.session_state.clear()
            st.rerun()

        except Exception as exc:
            st.error(f"Deactivation failed: {exc}")


# ====================== PRIVATE KEY SYSTEM ======================
if "user_key" not in st.session_state:
    st.session_state.user_key = None

if "private_key_input" not in st.session_state:
    st.session_state.private_key_input = ""

if "remember_private_key" not in st.session_state:
    st.session_state.remember_private_key = True

if "block_key_restore" not in st.session_state:
    st.session_state.block_key_restore = False

st.sidebar.markdown(
    '<div class="rk-private-space-title">📄 Your Private Space</div>',
    unsafe_allow_html=True,
)

remembered_private_key = None
if not st.session_state.block_key_restore:
    remembered_private_key = browser_storage.getItem(
        PRIVATE_KEY_STORAGE_NAME
    )

if (
    remembered_private_key
    and not st.session_state.user_key
    and not st.session_state.block_key_restore
):
    restored_key = str(remembered_private_key).strip()
    if restored_key and restored_key.lower() not in {"none", "null"}:
        st.session_state.user_key = restored_key
        st.session_state.private_key_input = restored_key
        st.session_state.remember_private_key = True

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
                st.sidebar.success(
                    "Private key remembered on this browser."
                )
            else:
                # Clear old private-key storage but preserve paid activation.
                _clear_all_browser_storage()
                _restore_license_after_storage_clear()
                st.sidebar.success(
                    "Private space opened for this session only."
                )

if not st.session_state.user_key:
    st.info(
        "👆 Your ReceiptKeeper licence is active. Enter your private-space "
        "key in the sidebar to open your receipt records."
    )
    st.stop()

st.sidebar.success(
    f"✅ Private space active: {st.session_state.user_key[:8]}..."
)

if st.sidebar.button(
    "🗑️ Forget Private Key on This Browser",
    use_container_width=True,
):
    # Clear all browser storage, then immediately restore only the licence.
    _clear_all_browser_storage()
    _restore_license_after_storage_clear()

    st.session_state.user_key = None
    st.session_state.private_key_input = ""
    st.session_state.remember_private_key = False
    st.session_state.block_key_restore = True

    for state_key in list(st.session_state.keys()):
        if state_key not in {
            "license_authorized",
            "license_storage_payload",
            "license_restore_checked",
            "license_warning",
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

            notes = st.text_area(
                "Notes (optional)",
                placeholder="Add a reason, tax detail, client reference, or reminder...",
                height=130,
                key="receipt_notes",
            )

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
    notes = st.text_area(
        "Purpose / Notes",
        placeholder="Describe the business purpose of this trip...",
        height=130,
        key="mileage_notes",
    )

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