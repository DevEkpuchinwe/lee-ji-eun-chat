from flask import Flask, request, jsonify, render_template, session, abort
from supabase import create_client
from flask_cors import CORS
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET = "chatimages"


# ====================== PAGE ROUTES ======================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ====================== USER FLOW ======================
@app.route("/start", methods=["POST"])
def start():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name", "Guest")

    conv_id = str(uuid.uuid4())

    supabase.table("conversations").insert({
        "id": conv_id,
        "user_id": user_id,
        "name": name,
        "display_name": name,           # Default to user's name
        "online": True,
        "typing": False,
        "last_seen": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({"id": conv_id})


@app.route("/update_status", methods=["POST"])
def update_status():
    data = request.json
    conv_id = data.get("conversation_id")
    online = data.get("online", True)

    supabase.table("conversations").update({
        "online": online,
        "last_seen": datetime.utcnow().isoformat()
    }).eq("id", conv_id).execute()

    return jsonify({"ok": True})


@app.route("/set_typing", methods=["POST"])
def set_typing():
    data = request.json
    conv_id = data.get("conversation_id")
    is_typing = data.get("typing", False)

    supabase.table("conversations").update({
        "typing": is_typing,
        "last_seen": datetime.utcnow().isoformat()
    }).eq("id", conv_id).execute()

    return jsonify({"ok": True})


@app.route("/send", methods=["POST"])
def send():
    conv_id = request.form.get("conversation_id")
    message = request.form.get("message")

    image_url = None
    if "image" in request.files and request.files["image"].filename:
        file = request.files["image"]
        filename = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_(BUCKET).upload(
            filename, file.read(), {"content-type": file.content_type or "image/jpeg"}
        )
        image_url = supabase.storage.from_(BUCKET).get_public_url(filename)

    supabase.table("messages").insert({
        "conversation_id": conv_id,
        "sender": "user",
        "message": message,
        "image_url": image_url
    }).execute()

    return jsonify({"status": "sent"})


@app.route("/messages/<conv_id>")
def messages(conv_id):
    res = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conv_id) \
        .order("created_at") \
        .execute()
    return jsonify(res.data)


# ====================== ADMIN ======================
def require_admin():
    if not session.get("admin"):
        abort(403)


@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    if data and data.get("password") == OWNER_PASSWORD:
        session["admin"] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "fail"}), 401


@app.route("/admin/check")
def admin_check():
    if session.get("admin"):
        return jsonify({"status": "ok"})
    return jsonify({"error": "unauthorized"}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"status": "ok"})


@app.route("/admin/conversations")
def admin_convs():
    require_admin()
    res = supabase.table("conversations").select("*").execute()
    return jsonify(res.data)


@app.route("/admin/rename_conversation/<conv_id>", methods=["POST"])
def rename_conversation(conv_id):
    require_admin()
    data = request.json
    new_name = data.get("display_name", "").strip()

    if not new_name:
        return jsonify({"error": "Name cannot be empty"}), 400

    supabase.table("conversations").update({
        "display_name": new_name
    }).eq("id", conv_id).execute()

    return jsonify({"status": "renamed", "display_name": new_name})


@app.route("/admin/conversation_status/<conv_id>")
def get_conversation_status(conv_id):
    require_admin()
    res = supabase.table("conversations") \
        .select("online, typing, last_seen, display_name, name, user_id") \
        .eq("id", conv_id) \
        .single() \
        .execute()
    return jsonify(res.data)


@app.route("/admin/delete_conversation/<id>", methods=["DELETE"])
def delete_conv(id):
    require_admin()
    supabase.table("messages").delete().eq("conversation_id", id).execute()
    supabase.table("conversations").delete().eq("id", id).execute()
    return jsonify({"status": "deleted"})


@app.route("/admin/messages/<conv_id>")
def admin_msgs(conv_id):
    require_admin()
    res = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conv_id) \
        .order("created_at") \
        .execute()
    return jsonify(res.data)


@app.route("/admin/send", methods=["POST"])
def admin_send():
    require_admin()
    conv_id = request.form.get("conversation_id")
    message = request.form.get("message")

    image_url = None
    if "image" in request.files and request.files["image"].filename:
        file = request.files["image"]
        filename = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_(BUCKET).upload(
            filename, file.read(), {"content-type": file.content_type or "image/jpeg"}
        )
        image_url = supabase.storage.from_(BUCKET).get_public_url(filename)

    supabase.table("messages").insert({
        "conversation_id": conv_id,
        "sender": "owner",
        "message": message,
        "image_url": image_url
    }).execute()

    return jsonify({"status": "sent"})


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True)