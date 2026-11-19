@st.cache_data(ttl=3600)
def get_available_chat_models():
    blocked = ("image", "tts", "live", "embed", "aqa", "vision", "pro", "research", "computer", "robotics", "thinking")
    try:
        available = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "gemini" in m.name and not any(b in m.name.lower() for b in blocked)
        ]
        ordered = [m for m in PREFERRED_MODELS if m in available]
        others = [m for m in available if m not in ordered]
        return (ordered + others)[:4] if (ordered or others) else PREFERRED_MODELS[:3]
    except Exception:
        return PREFERRED_MODELS[:3]

supabase = None
supa_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
supa_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if supa_url and supa_key:
    try:
        supabase = create_client(supa_url, supa_key)
    except Exception:
        supabase = None

# --- AUTHENTICATION GATE (Stay Signed In) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email and supabase and "rt" in st.query_params:
    try:
        refreshed = supabase.auth.refresh_session(st.query_params["rt"])
        if refreshed and refreshed.user:
            st.session_state.user_email = refreshed.user.email
            if refreshed.session:
                st.query_params["rt"] = refreshed.session.refresh_token
    except Exception:
        st.query_params.clear()

if not st.session_state.user_email:
    col_l, col_mid, col_r = st.columns([1, 1.4, 1])
    with col_mid:
        theme_choice = st.selectbox(
            "🎨 Theme:",
            list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.app_theme),
        )
        if theme_choice != st.session_state.app_theme:
            st.session_state.app_theme = theme_choice
            st.rerun()

        st.title("⚡ Welcome to Spark AI")
        st.caption("Sign in to access your private AI workspace & synced chat threads.")
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Sign In", "✨ Create Account", "🚀 Guest Mode"])

        with auth_tab1:
            login_email = st.text_input("Email", key="login_email")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif login_email and login_pass:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user_email = res.user.email
                        if res.session:
                            st.query_params["rt"] = res.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        with auth_tab2:
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif reg_email and len(reg_pass) >= 6:
                    try:
                        res = supabase.auth.sign_up({"email": reg_email, "password": reg_pass})
                        if res.user:
                            st.session_state.user_email = res.user.email
                            if res.session:
                                st.query_params["rt"] = res.session.refresh_token
                            st.success("Account created! Loading Spark AI...")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
                else:
                    st.warning("Enter a valid email and a password with at least 6 characters.")

        with auth_tab3:
            st.info("Try Spark AI without saving threads to the cloud.")
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user_email = "guest@local"
                st.rerun()
    st.stop()

# --- FOCUS MODES ---
NO_SLANG_RULE = " You were created by Ibrahim Khaliq. If anyone asks who created, built, or made you, always answer that you are Spark AI, created by Ibrahim Khaliq. Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- FULL UNICODE EMOJI DATABASE (ALL EMOJIS + NAMES FOR SEARCH) ---
@st.cache_data
def get_all_unicode_emojis():
    ranges = [
        (0x1F300, 0x1F5FF),
        (0x1F600, 0x1F64F),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]
    emojis = []
    for start, end in ranges:
        for cp in range(start, end + 1):
            ch = chr(cp)
            try:
                name = unicodedata.name(ch).title()
                if unicodedata.category(ch) == "So":
                    emojis.append(f"{ch}  {name}")
            except ValueError:
                continue
    return emojis

ALL_EMOJIS = get_all_unicode_emojis()

# --- AVATAR & SUPABASE SYNC HELPERS ---
def encode_avatar_image(uploaded_img):
    img = Image.open(uploaded_img).convert("RGBA")
    img.thumbnail((96, 96))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def load_avatars_from_supabase():
    if not supabase or st.session_state.user_email == "guest@local":
        return "💎", "⚡"
    try:
        res = (
            supabase.table("spark_profiles")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .execute()
        )
        if res.data:
            return res.data[0].get("user_avatar", "💎"), res.data[0].get("bot_avatar", "⚡")
    except Exception:
        pass
    return "💎", "⚡"

def save_avatars_to_supabase(u_av, b_av):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        supabase.table("spark_profiles").upsert({
            "user_email": st.session_state.user_email,
            "user_avatar": u_av,
            "bot_avatar": b_av
        }).execute()
    except Exception:
        pass

if "user_avatar" not in st.session_state or "bot_avatar" not in st.session_state:
    u_av, b_av = load_avatars_from_supabase()
    st.session_state.user_avatar = u_av
    st.session_state.bot_avatar = b_av  
@st.cache_data(ttl=3600)
def get_available_chat_models():
    blocked = ("image", "tts", "live", "embed", "aqa", "vision", "pro", "research", "computer", "robotics", "thinking")
    try:
        available = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "gemini" in m.name and not any(b in m.name.lower() for b in blocked)
        ]
        ordered = [m for m in PREFERRED_MODELS if m in available]
        others = [m for m in available if m not in ordered]
        return (ordered + others)[:4] if (ordered or others) else PREFERRED_MODELS[:3]
    except Exception:
        return PREFERRED_MODELS[:3]

supabase = None
supa_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
supa_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if supa_url and supa_key:
    try:
        supabase = create_client(supa_url, supa_key)
    except Exception:
        supabase = None

# --- AUTHENTICATION GATE (Stay Signed In) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email and supabase and "rt" in st.query_params:
    try:
        refreshed = supabase.auth.refresh_session(st.query_params["rt"])
        if refreshed and refreshed.user:
            st.session_state.user_email = refreshed.user.email
            if refreshed.session:
                st.query_params["rt"] = refreshed.session.refresh_token
    except Exception:
        st.query_params.clear()

if not st.session_state.user_email:
    col_l, col_mid, col_r = st.columns([1, 1.4, 1])
    with col_mid:
        theme_choice = st.selectbox(
            "🎨 Theme:",
            list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.app_theme),
        )
        if theme_choice != st.session_state.app_theme:
            st.session_state.app_theme = theme_choice
            st.rerun()

        st.title("⚡ Welcome to Spark AI")
        st.caption("Sign in to access your private AI workspace & synced chat threads.")
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Sign In", "✨ Create Account", "🚀 Guest Mode"])

        with auth_tab1:
            login_email = st.text_input("Email", key="login_email")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif login_email and login_pass:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user_email = res.user.email
                        if res.session:
                            st.query_params["rt"] = res.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        with auth_tab2:
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif reg_email and len(reg_pass) >= 6:
                    try:
                        res = supabase.auth.sign_up({"email": reg_email, "password": reg_pass})
                        if res.user:
                            st.session_state.user_email = res.user.email
                            if res.session:
                                st.query_params["rt"] = res.session.refresh_token
                            st.success("Account created! Loading Spark AI...")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
                else:
                    st.warning("Enter a valid email and a password with at least 6 characters.")

        with auth_tab3:
            st.info("Try Spark AI without saving threads to the cloud.")
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user_email = "guest@local"
                st.rerun()
    st.stop()

# --- FOCUS MODES ---
NO_SLANG_RULE = " You were created by Ibrahim Khaliq. If anyone asks who created, built, or made you, always answer that you are Spark AI, created by Ibrahim Khaliq. Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- FULL UNICODE EMOJI DATABASE (ALL EMOJIS + NAMES FOR SEARCH) ---
@st.cache_data
def get_all_unicode_emojis():
    ranges = [
        (0x1F300, 0x1F5FF),
        (0x1F600, 0x1F64F),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]
    emojis = []
    for start, end in ranges:
        for cp in range(start, end + 1):
            ch = chr(cp)
            try:
                name = unicodedata.name(ch).title()
                if unicodedata.category(ch) == "So":
                    emojis.append(f"{ch}  {name}")
            except ValueError:
                continue
    return emojis

ALL_EMOJIS = get_all_unicode_emojis()

# --- AVATAR & SUPABASE SYNC HELPERS ---
def encode_avatar_image(uploaded_img):
    img = Image.open(uploaded_img).convert("RGBA")
    img.thumbnail((96, 96))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def load_avatars_from_supabase():
    if not supabase or st.session_state.user_email == "guest@local":
        return "💎", "⚡"
    try:
        res = (
            supabase.table("spark_profiles")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .execute()
        )
        if res.data:
            return res.data[0].get("user_avatar", "💎"), res.data[0].get("bot_avatar", "⚡")
    except Exception:
        pass
    return "💎", "⚡"

def save_avatars_to_supabase(u_av, b_av):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        supabase.table("spark_profiles").upsert({
            "user_email": st.session_state.user_email,
            "user_avatar": u_av,
            "bot_avatar": b_av
        }).execute()
    except Exception:
        pass

if "user_avatar" not in st.session_state or "bot_avatar" not in st.session_state:
    u_av, b_av = load_avatars_from_supabase()
    st.session_state.user_avatar = u_av
    st.session_state.bot_avatar = b_av
def load_threads_from_supabase():
    if not supabase or st.session_state.user_email == "guest@local":
        return None
    try:
        res = (
            supabase.table("spark_threads")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .order("updated_at")
            .execute()
        )
        if res.data:
            loaded = {}
            for row in res.data:
                loaded[row["thread_id"]] = {
                    "title": row["title"],
                    "messages": json.loads(row["messages_json"])
                }
            return loaded
    except Exception:
        return None
    return None

def save_thread_to_supabase(thread_id, thread_data):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        serializable_msgs = []
        for m in thread_data["messages"]:
            clean_m = {"role": m["role"], "content": m.get("content", "")}
            if m.get("file_name"):
                clean_m["file_name"] = m["file_name"]
            serializable_msgs.append(clean_m)

        supabase.table("spark_threads").upsert({
            "thread_id": thread_id,
            "user_email": st.session_state.user_email,
            "title": thread_data["title"],
            "messages_json": json.dumps(serializable_msgs)
        }).execute()
    except Exception:
        pass

def delete_thread_from_supabase(thread_id):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        supabase.table("spark_threads").delete().eq("thread_id", thread_id).execute()
    except Exception:
        pass

# --- MULTI-THREAD SESSION STATE ---
if "threads" not in st.session_state:
    saved_threads = load_threads_from_supabase()
    if saved_threads:
        st.session_state.threads = saved_threads
        st.session_state.current_thread_id = next(iter(saved_threads))
    else:
        first_id = str(uuid.uuid4())
        st.session_state.threads = {first_id: {"title": "New Chat 1", "messages": []}}
        st.session_state.current_thread_id = first_id

if "audio_cache" not in st.session_state:
    st.session_state.audio_cache = {}
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []

if st.session_state.current_thread_id not in st.session_state.threads:
    st.session_state.current_thread_id = next(iter(st.session_state.threads))

active_thread = st.session_state.threads[st.session_state.current_thread_id]

# --- HELPER FUNCTIONS ---
def create_new_thread():
    new_id = str(uuid.uuid4())
    chat_num = len(st.session_state.threads) + 1
    st.session_state.threads[new_id] = {"title": f"New Chat {chat_num}", "messages": []}
    st.session_state.current_thread_id = new_id
    save_thread_to_supabase(new_id, st.session_state.threads[new_id])

def web_search_ddg(query, max_results=6):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

def generate_pptx(slides_data):
    prs = Presentation()
    for slide_info in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_info.get("title", "Slide")
        body = slide.placeholders[1].text_frame
        body.clear()
        for idx, point in enumerate(slide_info.get("bullets", [])):
            p = body.paragraphs[0] if idx == 0 else body.add_paragraph()
            p.text = point
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

def text_to_speech(text, cache_key):
    if cache_key not in st.session_state.audio_cache:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        tts = gTTS(text=clean_text[:1500], lang="en")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.session_state.audio_cache[cache_key] = fp.getvalue()
    return st.session_state.audio_cache[cache_key]

def generate_with_fallback(contents, config):
    models_to_try = get_available_chat_models()
    if st.session_state.get("working_model") in models_to_try:
        wm = st.session_state["working_model"]
        models_to_try = [wm] + [m for m in models_to_try if m != wm]

    last_error = None
    for model_name in models_to_try:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            st.session_state["working_model"] = model_name
            return res
        except Exception as e:
            last_error = e
            err_str = str(e)
            if any(code in err_str for code in ["503", "429", "404", "400", "UNAVAILABLE", "NOT_FOUND"]):
                continue
            raise e
    raise last_error

def get_spark_reply(action_mode, system_instruction, user_text, gemini_contents):
    if action_mode == "🌐 Live Web Search":
        results = web_search_ddg(user_text, max_results=5)
        context_lines = [f"- {r.get('title')}: {r.get('body')} ({r.get('href')})" for r in results]
        search_prompt = (
            f"User question: {user_text}\n\n"
            f"Live Web Search Results:\n" + "\n".join(context_lines) +
            "\n\nAnswer clearly using the web search results and include clickable markdown links to sources."
        )
        response = generate_with_fallback(
            contents=search_prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return {"role": "assistant", "content": response.text}

    if action_mode == "🎨 Generate AI Image":
        for img_model in ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]:
            try:
                res = client.models.generate_content(
                    model=img_model,
                    contents=user_text or "A futuristic glowing spark",
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
                )
                for part in res.candidates[0].content.parts:
                    if part.inline_data:
                        gen_img = Image.open(io.BytesIO(part.inline_data.data))
                        return {
                            "role": "assistant",
                            "content": f"Here is your generated image for: **{user_text}**",
                            "image": gen_img,
                        }
            except Exception:
                continue
        raise RuntimeError("Image generation model is currently unavailable for this API key.")

    if action_mode == "📊 Build Presentation Slide":
        ppt_prompt = (
            f"Create a 5-slide presentation about: {user_text}. "
            "Return ONLY valid JSON as a list of objects with keys 'title' and 'bullets' (list of strings)."
        )
        response = generate_with_fallback(
            contents=ppt_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        slides_data = json.loads(response.text)
        pptx_file = generate_pptx(slides_data)
        return {
            "role": "assistant",
            "content": f"I built a **{len(slides_data)}-slide presentation** on **{user_text}**.",
            "pptx_bytes": pptx_file.getvalue()
        }

    response = generate_with_fallback(
        contents=gemini_contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )
    return {"role": "assistant", "content": response.text}

# --- SIDEBAR CONTROLS & CHAT THREADS ---
with st.sidebar:
    st.title("⚡ Spark AI")
    st.caption(f"👤 Signed in: **{st.session_state.user_email}**")
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.user_email = None
        st.session_state.pop("threads", None)
        st.session_state.pop("user_avatar", None)
        st.session_state.pop("bot_avatar", None)
        st.query_params.clear()
        st.rerun()

    st.divider()
    selected_theme = st.selectbox(
        "🎨 App Theme:",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.app_theme),
    )
    if selected_theme != st.session_state.app_theme:
        st.session_state.app_theme = selected_theme
        st.rerun()

    # --- CUSTOMIZE AVATARS (ALL UNICODE EMOJIS + UPLOADED PHOTOS) ---
    with st.expander("🎭 Customize Avatars (You & Spark)", expanded=False):
        av_tab1, av_tab2 = st.tabs(["👤 Your Icon", "⚡ Spark Icon"])

        with av_tab1:
            u_choice = st.selectbox(f"Browse All {len(ALL_EMOJIS)} Emojis (type to search):", ALL_EMOJIS, key="u_all_emojis")
            u_custom = st.text_input("Or paste any emoji:", key="u_custom_emoji")
            u_photo = st.file_uploader("Or upload your image:", type=["png", "jpg", "jpeg", "webp"], key="u_photo")
            if st.button("Save Your Avatar", use_container_width=True):
                if u_photo is not None:
                    st.session_state.user_avatar = encode_avatar_image(u_photo)
                elif u_custom.strip():
                    st.session_state.user_avatar = u_custom.strip()
                else:
                    st.session_state.user_avatar = u_choice.split("  ")[0]
                save_avatars_to_supabase(st.session_state.user_avatar, st.session_state.bot_avatar)
                st.rerun()

        with av_tab2:
            b_choice = st.selectbox(f"Browse All {len(ALL_EMOJIS)} Emojis for Spark:", ALL_EMOJIS, key="b_all_emojis")
            b_custom = st.text_input("Or paste any emoji for Spark:", key="b_custom_emoji")
