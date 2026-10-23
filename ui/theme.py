"""KavachED visual system and responsive animated background."""

from __future__ import annotations

import streamlit as st


def inject_theme(dark: bool | str = False, reduced: bool = False) -> None:
    """Apply consistent light/dark design tokens and responsive styling."""
    dark = dark == "dark" if isinstance(dark, str) else dark
    palette = (
        {
            "bg": "#0b1220",
            "surface": "#131f33",
            "surface2": "#17243a",
            "border": "#475569",
            "text": "#f1f5f9",
            "muted": "#aab8ca",
            "accentText": "#f5a524",
            "successText": "#4ade80",
        }
        if dark
        else {
            "bg": "#f4f7fb",
            "surface": "#ffffff",
            "surface2": "#eef3f9",
            "border": "#c7d2df",
            "text": "#14243a",
            "muted": "#52647a",
            "accentText": "#805000",
            "successText": "#087443",
        }
    )
    motion = "animation:none!important;transition:none!important" if reduced else ""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

        :root {{
            --bg: {palette["bg"]};
            --surface: {palette["surface"]};
            --surface-2: {palette["surface2"]};
            --border: {palette["border"]};
            --text: {palette["text"]};
            --text-muted: {palette["muted"]};
            --muted: {palette["muted"]};
            --accent-text: {palette["accentText"]};
            --success-text: {palette["successText"]};
            --primary: #f5a524;
            --navy: #0b1b3a;
            --success: #22a06b;
            --warning: #e5a100;
            --danger: #e5484d;
            --radius: 18px;
        }}

        html, body, .stApp, [data-testid="stAppViewContainer"], .main {{
            min-height: 100vh !important;
            height: auto !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            font-family: Inter, sans-serif;
            color: var(--text);
        }}
        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}
        .block-container {{
            max-width: 1440px;
            padding-top: 3.2rem !important;
            padding-bottom: 5rem !important;
            position: relative;
            z-index: 2;
        }}
        [data-testid="stHeader"] {{
            background: transparent;
            height: 2.8rem;
        }}
        [data-testid="stToolbar"], #MainMenu, footer {{
            visibility: hidden;
        }}
        h1, h2, h3, h4 {{
            color: var(--text);
            font-family: 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -.035em;
        }}
        a, a:visited {{ color: var(--accent-text) !important; }}
        .stMarkdown, [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
        [data-testid="stExpander"] summary,
        [data-testid="stDialog"], [data-testid="stDialog"] *,
        [data-testid="stToast"], [data-testid="stToast"] * {{
            color: var(--text);
        }}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] *,
        .stCaption, .stCaption * {{
            color: var(--text-muted) !important;
        }}
        label, [data-testid="stWidgetLabel"] label {{
            color: var(--text) !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stExpander"],
        [data-testid="stPopover"] {{
            border-color: var(--border) !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 22px;
            background: var(--surface);
            padding: 12px;
        }}
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="input"] input,
        textarea {{
            background: var(--surface-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            -webkit-text-fill-color: var(--text) !important;
        }}
        [data-testid="stFileUploaderDropzone"] {{
            background: var(--surface-2) !important;
            border: 1px dashed var(--border) !important;
        }}
        [data-testid="stFileUploaderDropzone"] * {{
            color: var(--text) !important;
        }}
        input::placeholder, textarea::placeholder,
        [data-baseweb="input"] input::placeholder {{
            color: var(--text-muted) !important;
            opacity: 1 !important;
            -webkit-text-fill-color: var(--text-muted) !important;
        }}
        [data-baseweb="select"] > div {{
            background: var(--surface-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
        }}
        [data-baseweb="select"] input,
        [data-baseweb="select"] [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] [aria-selected],
        [data-baseweb="select"] span {{
            color: var(--text) !important;
            -webkit-text-fill-color: var(--text) !important;
        }}
        [data-baseweb="select"] svg {{
            fill: var(--text-muted) !important;
            color: var(--text-muted) !important;
        }}
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        ul[role="listbox"],
        li[role="option"] {{
            background: var(--surface) !important;
            color: var(--text) !important;
        }}
        [data-baseweb="popover"] *,
        [data-baseweb="menu"] *,
        ul[role="listbox"] *,
        li[role="option"] * {{
            color: var(--text) !important;
        }}
        li[role="option"]:hover,
        li[role="option"][aria-selected="true"],
        li[role="option"][data-highlighted="true"] {{
            background: rgba(245,165,36,.15) !important;
        }}
        [data-baseweb="tab-list"] {{ gap: 8px; }}
        [data-baseweb="tab"] {{
            color: var(--text-muted) !important;
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--text) !important;
            border-color: var(--primary) !important;
        }}
        [data-testid="stExpander"] {{
            background: var(--surface);
            color: var(--text);
        }}
        [role="tooltip"], [data-testid="stTooltipContent"] {{
            background: var(--surface) !important;
            color: var(--text) !important;
            border: 1px solid var(--border);
        }}
        [role="tooltip"] *, [data-testid="stTooltipContent"] * {{
            color: var(--text) !important;
        }}
        [data-testid="stPopover"] > button,
        [data-testid="stExpander"] summary {{
            color: var(--text) !important;
        }}
        [data-testid="stPopover"] {{
            color: var(--text);
            background: var(--surface);
        }}
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
        }}
        [data-testid="stDataFrame"] iframe {{
            color-scheme: {"dark" if dark else "light"};
        }}
        code, pre {{
            color: var(--text) !important;
            background: var(--surface-2) !important;
        }}
        [data-testid="stChatMessage"] {{
            background: transparent !important;
            border: 0 !important;
            color: var(--text) !important;
        }}
        [data-testid="stChatMessageAvatarUser"] + div,
        [data-testid="stChatMessageAvatarAssistant"] + div {{
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            padding: 10px 14px !important;
            color: var(--text) !important;
        }}
        [data-testid="stChatMessageAvatarUser"] + div {{
            background: rgba(245,165,36,.14) !important;
        }}
        [data-testid="stChatMessageAvatarAssistant"] + div {{
            background: var(--surface-2) !important;
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
            flex-direction: row-reverse;
        }}
        [data-testid="stMetric"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(17,35,64,.05);
        }}
        [data-testid="stMetricLabel"] {{ color: var(--text-muted) !important; }}
        [data-testid="stMetricValue"] {{ color: var(--text) !important; }}
        [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {{
            color: var(--success-text) !important;
        }}
        [data-testid="stSliderThumbValue"] {{
            color: #0B1B3A !important;
            font-weight: 600;
        }}
        button[kind="secondary"], button[kind="secondaryFormSubmit"],
        [data-testid="stBaseButton-secondary"],
        [data-testid="stBaseButton-secondaryFormSubmit"] {{
            background: transparent !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
        }}
        button[kind="secondary"] p, button[kind="secondary"] span,
        button[kind="secondaryFormSubmit"] p, button[kind="secondaryFormSubmit"] span,
        [data-testid="stBaseButton-secondary"] p,
        [data-testid="stBaseButton-secondary"] span,
        [data-testid="stBaseButton-secondaryFormSubmit"] p,
        [data-testid="stBaseButton-secondaryFormSubmit"] span {{
            color: inherit !important;
        }}
        button[kind="secondary"]:hover,
        button[kind="secondaryFormSubmit"]:hover,
        [data-testid="stBaseButton-secondary"]:hover,
        [data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
            border-color: var(--primary) !important;
            color: var(--accent-text) !important;
        }}
        button[kind="secondary"]:hover p,
        button[kind="secondary"]:hover span,
        button[kind="secondaryFormSubmit"]:hover p,
        button[kind="secondaryFormSubmit"]:hover span,
        [data-testid="stBaseButton-secondary"]:hover p,
        [data-testid="stBaseButton-secondary"]:hover span,
        [data-testid="stBaseButton-secondaryFormSubmit"]:hover p,
        [data-testid="stBaseButton-secondaryFormSubmit"]:hover span {{
            color: var(--accent-text) !important;
        }}
        button[kind="primary"], button[kind="primaryFormSubmit"],
        [data-testid="stBaseButton-primary"],
        [data-testid="stBaseButton-primaryFormSubmit"] {{
            background: #F5A524 !important;
            border: 1px solid #F5A524 !important;
            color: #0B1B3A !important;
            font-weight: 600 !important;
        }}
        button[kind="primary"] p, button[kind="primary"] span,
        button[kind="primaryFormSubmit"] p, button[kind="primaryFormSubmit"] span,
        [data-testid="stBaseButton-primary"] p,
        [data-testid="stBaseButton-primary"] span,
        [data-testid="stBaseButton-primaryFormSubmit"] p,
        [data-testid="stBaseButton-primaryFormSubmit"] span {{
            color: #0B1B3A !important;
            font-weight: 600 !important;
        }}
        button:disabled {{
            opacity: .65;
        }}
        ::selection {{
            background: rgba(245,165,36,.3);
            color: var(--text);
        }}

        [data-testid="stSidebar"] {{
            background: #0b1b3a;
            border-right: 1px solid #293a55;
            --text: #f4f7fb;
            --surface: #132442;
            --surface-2: #10203b;
            --border: #354761;
            --text-muted: #bdc9d9;
            --muted: #bdc9d9;
            --accent-text: #F5A524;
            color: var(--text);
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
            background: transparent !important;
            padding: 0 !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: var(--text-muted);
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
            background: rgba(245,165,36,.12) !important;
            color: #ffffff !important;
            border: 0 !important;
            border-left: 3px solid #F5A524 !important;
            font-weight: 700 !important;
            text-align: left;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] span {{
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
            height: 40px;
            border: 1px solid transparent !important;
            border-radius: 12px !important;
            color: #bdc9d9 !important;
            text-align: left;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] span {{
            color: inherit !important;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
            background: rgba(255,255,255,.08) !important;
            color: #ffffff !important;
            border-color: transparent !important;
        }}
        .sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 16px;
            margin: -8px -8px 2px;
        }}
        .sidebar-brand img {{ width: 32px; height: 32px; }}
        .sidebar-brand-name {{
            color: #ffffff;
            font: 700 23px 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -.04em;
        }}
        .sidebar-brand-name span {{ color: #F5A524; }}
        .sidebar-subtitle {{
            color: #bdc9d9;
            font-size: 10px;
            letter-spacing: .12em;
            margin: 0 8px 18px;
            text-transform: uppercase;
        }}
        .nav-section {{
            color: #90a0b7;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .14em;
            margin: 14px 8px 6px;
        }}
        .kavach-chat-area {{
            height: 260px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 8px 4px;
            margin: 4px 0 10px;
            border-radius: 12px;
            background: rgba(4,13,29,.32);
        }}
        .chat-message {{
            display: flex;
            align-items: flex-start;
            gap: 7px;
            max-width: 95%;
        }}
        .chat-message.user {{ align-self: flex-end; flex-direction: row-reverse; }}
        .chat-avatar {{
            flex: 0 0 22px;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            background: rgba(245,165,36,.2);
            color: #F5A524;
            font-size: 11px;
            font-weight: 700;
        }}
        .chat-bubble {{
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 8px 10px;
            color: var(--text);
            font-size: 12px;
            line-height: 1.45;
            overflow-wrap: anywhere;
            background: var(--surface-2);
        }}
        .chat-message.user .chat-bubble {{ background: rgba(245,165,36,.14); }}
        .chat-read-more {{
            display: block;
            color: #F5A524;
            margin-top: 5px;
            font-size: 11px;
        }}
        .suggestion-chip {{
            font-size: 11px;
            white-space: normal;
        }}
        .sidebar-account {{
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid #354761;
            border-radius: 14px;
            background: #132442;
            padding: 10px;
            margin: 16px 0 8px;
        }}
        .account-avatar {{
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: rgba(245,165,36,.18);
            color: #F5A524;
            font-weight: 700;
        }}
        .account-name {{ color: #ffffff; font-weight: 600; font-size: 12px; }}
        .account-role {{ color: #bdc9d9; font-size: 10px; }}

        .hero-shell {{
            padding: 32px;
            border: 1px solid var(--border);
            border-radius: 24px;
            background: linear-gradient(125deg, var(--surface), var(--surface-2));
            box-shadow: 0 20px 55px rgba(17,35,64,.08);
            margin-bottom: 22px;
        }}
        .hero-shell h1 {{ margin: 0 0 8px; font-size: clamp(27px, 3vw, 38px); }}
        .hero-shell p {{ color: var(--text-muted); margin: 0; }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 22px;
            box-shadow: 0 10px 28px rgba(17,35,64,.055);
            backdrop-filter: blur(12px);
            min-width: 0;
            overflow-wrap: anywhere;
        }}
        .eyebrow {{
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: var(--accent-text);
        }}
        .muted {{ color: var(--text-muted); }}
        .risk-high, .risk-medium, .risk-low {{
            display: inline-block;
            border-radius: 999px;
            padding: 5px 11px;
            font-size: 12px;
            font-weight: 700;
        }}
        .risk-high {{ background: #ffe6e5; color: #842124; }}
        .risk-medium {{ background: #fff2cc; color: #684400; }}
        .risk-low {{ background: #dcf5e9; color: #0d5335; }}
        .page-spacer {{ height: 14px; }}
        .topline {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin: 0 0 18px;
            color: var(--text-muted);
            font-size: 13px;
        }}
        .topline-left {{ min-width: 0; overflow-wrap: anywhere; }}
        .st-key-topbar-controls [data-testid="stHorizontalBlock"] {{
            align-items: center;
            gap: 12px !important;
        }}
        .topbar-profile {{
            min-width: 0;
            max-width: 100%;
            overflow: hidden;
        }}
        .topbar-profile .account-name {{
            max-width: 105px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .landing-wrap {{
            display: grid;
            grid-template-columns: minmax(0, 1.05fr) minmax(340px, .95fr);
            gap: 40px;
            align-items: center;
            min-height: 82vh;
        }}
        .landing-hero {{ padding: clamp(12px, 4vw, 50px) 0; }}
        .landing-brand-main {{ color: var(--text); }}
        .landing-brand-accent {{ color: var(--accent-text); }}
        .landing-hero h1 {{
            font-size: clamp(42px, 6vw, 72px);
            line-height: 1.03;
            margin: 26px 0 16px;
            color: var(--text);
        }}
        .landing-hero .sub {{ font-size: 19px; color: var(--text-muted); margin-bottom: 22px; }}
        .quote {{
            border-left: 3px solid var(--primary);
            padding: 12px 16px;
            background: var(--surface);
            border-radius: 0 14px 14px 0;
            animation: fade-in 1s ease both;
        }}
        .chip-row {{ display: flex; flex-wrap: wrap; gap: 9px; margin-top: 24px; }}
        .feature-chip {{
            border: 1px solid var(--border);
            border-radius: 99px;
            padding: 8px 12px;
            background: var(--surface);
            font-size: 12px;
            color: var(--text-muted);
        }}
        .auth-card {{
            padding: clamp(20px, 3vw, 34px);
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 24px 70px rgba(17,35,64,.13);
            backdrop-filter: blur(18px);
        }}
        .background-orbs {{
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
            background:
                radial-gradient(ellipse at 14% 20%, rgba(245,165,36,.13), transparent 35%),
                radial-gradient(ellipse at 82% 74%, rgba(34,117,180,.10), transparent 40%);
        }}
        .background-orbs:before {{
            content: '';
            position: absolute;
            inset: -35%;
            background-image:
                linear-gradient(rgba(114,144,180,.08) 1px, transparent 1px),
                linear-gradient(90deg, rgba(114,144,180,.08) 1px, transparent 1px);
            background-size: 54px 54px;
            transform: perspective(500px) rotateX(62deg) translateY(45%);
            animation: grid-drift 38s linear infinite;
            mask-image: linear-gradient(transparent, black 30%, transparent 95%);
        }}
        .orb {{
            position: absolute;
            width: 90px;
            height: 90px;
            border: 1px solid rgba(245,165,36,.2);
            border-radius: 24px;
            transform: rotate(22deg);
            background: linear-gradient(140deg, rgba(255,255,255,.15), rgba(245,165,36,.045));
            box-shadow: inset 0 0 30px rgba(255,255,255,.05);
            animation: float 13s ease-in-out infinite;
        }}
        .orb.one {{ top: 17%; left: 8%; }}
        .orb.two {{ top: 64%; left: 35%; width: 56px; height: 56px; animation-delay: -4s; }}
        .orb.three {{ top: 16%; right: 14%; width: 120px; height: 120px; animation-delay: -7s; }}
        .orb.four {{ bottom: 8%; right: 10%; width: 65px; height: 65px; animation-delay: -2s; }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0) rotate(22deg); }}
            50% {{ transform: translateY(-22px) rotate(38deg); }}
        }}
        @keyframes grid-drift {{ to {{ background-position: 0 108px, 108px 0; }} }}
        @keyframes fade-in {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: none; }}
        }}
        [data-testid="stAppViewContainer"] {{ position: relative; z-index: 1; }}
        @media (max-width: 900px) {{
            .landing-wrap {{ grid-template-columns: 1fr; gap: 10px; min-height: auto; }}
            .landing-hero {{ padding: 10px 0; }}
            .landing-hero h1 {{ font-size: 46px; }}
            .auth-card {{ margin-bottom: 24px; }}
            .hero-shell {{ padding: 24px; }}
            .st-key-topbar-controls [data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap;
                row-gap: 8px !important;
            }}
            .st-key-topbar-controls [data-testid="stColumn"]:first-child {{
                flex: 1 1 100% !important;
            }}
            .st-key-topbar-controls [data-testid="stColumn"]:nth-child(2),
            .st-key-topbar-controls [data-testid="stColumn"]:nth-child(3),
            .st-key-topbar-controls [data-testid="stColumn"]:nth-child(4) {{
                flex: 0 0 54px !important;
                width: 54px !important;
            }}
            .st-key-topbar-controls [data-testid="stColumn"]:nth-child(2) {{
                flex-basis: 72px !important;
                width: 72px !important;
            }}
            .st-key-topbar-controls [data-testid="stColumn"]:last-child {{
                flex: 1 1 120px !important;
                min-width: 120px;
            }}
        }}
        @media (max-width: 640px) {{
            .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
            .card {{ padding: 17px; }}
            .landing-hero h1 {{ font-size: 40px; }}
            .topline {{ align-items: flex-start; flex-direction: column; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            * {{ {motion} }}
            .background-orbs:before {{ animation: none; }}
        }}
        </style>
        <div class="background-orbs">
            <span class="orb one"></span>
            <span class="orb two"></span>
            <span class="orb three"></span>
            <span class="orb four"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
