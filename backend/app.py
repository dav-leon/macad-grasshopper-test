import os
import json
import uuid
import datetime
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-production")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _decode(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({"error": "No token provided"}), 401
        payload = _decode(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({"error": "No token provided"}), 401
        payload = _decode(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        if not payload.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    users = read_json(USERS_FILE)

    if any(u["username"] == username for u in users):
        return jsonify({"error": "Username already taken"}), 409

    is_admin = len(users) == 0  # first user becomes admin

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": password_hash,
        "is_admin": is_admin,
        "results": [],
    }
    users.append(user)
    write_json(USERS_FILE, users)

    return jsonify({"message": "Registered successfully", "is_admin": is_admin}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    users = read_json(USERS_FILE)
    user = next((u for u in users if u["username"] == username), None)

    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid username or password"}), 401

    payload = {
        "id": user["id"],
        "username": user["username"],
        "is_admin": user["is_admin"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "is_admin": user["is_admin"],
        },
    })


# ---------------------------------------------------------------------------
# Quiz routes
# ---------------------------------------------------------------------------

@app.route("/api/quiz", methods=["GET"])
@require_auth
def get_quiz():
    questions = read_json(QUESTIONS_FILE)
    safe = [
        {
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "time_limit": q["time_limit"],
            "image": q.get("image"),
        }
        for q in questions
    ]
    return jsonify(safe)


@app.route("/api/quiz/submit", methods=["POST"])
@require_auth
def submit_quiz():
    data = request.get_json() or {}
    answers = data.get("answers", {})   # {str(question_id): option_index | null}
    time_taken = data.get("time_taken", 0)

    questions = read_json(QUESTIONS_FILE)

    score = 0
    results = []

    for q in questions:
        user_answer = answers.get(str(q["id"]))
        is_correct = user_answer == q["answer"]
        if is_correct:
            score += 1
        results.append({
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "user_answer": user_answer,
            "correct_answer": q["answer"],
            "is_correct": is_correct,
        })

    # Persist result
    users = read_json(USERS_FILE)
    user_id = request.current_user["id"]
    for u in users:
        if u["id"] == user_id:
            u["results"].append({
                "date": datetime.datetime.utcnow().isoformat(),
                "score": score,
                "total": len(questions),
                "time_taken": time_taken,
            })
            break
    write_json(USERS_FILE, users)

    return jsonify({"score": score, "total": len(questions), "results": results})


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route("/api/admin/questions", methods=["GET"])
@require_admin
def admin_get_questions():
    return jsonify(read_json(QUESTIONS_FILE))


@app.route("/api/admin/questions", methods=["POST"])
@require_admin
def admin_add_question():
    data = request.get_json() or {}
    questions = read_json(QUESTIONS_FILE)

    new_id = max((q["id"] for q in questions), default=0) + 1
    question = {
        "id": new_id,
        "question": data.get("question", "").strip(),
        "options": data.get("options", []),
        "answer": data.get("answer", 0),
        "time_limit": data.get("time_limit", 30),
        "image": data.get("image"),
    }

    if not question["question"] or len(question["options"]) != 4:
        return jsonify({"error": "Invalid question data"}), 400

    questions.append(question)
    write_json(QUESTIONS_FILE, questions)
    return jsonify(question), 201


@app.route("/api/admin/questions/<int:qid>", methods=["PUT"])
@require_admin
def admin_update_question(qid):
    data = request.get_json() or {}
    questions = read_json(QUESTIONS_FILE)

    for i, q in enumerate(questions):
        if q["id"] == qid:
            questions[i] = {
                "id": qid,
                "question": data.get("question", q["question"]),
                "options": data.get("options", q["options"]),
                "answer": data.get("answer", q["answer"]),
                "time_limit": data.get("time_limit", q["time_limit"]),
                "image": data.get("image", q.get("image")),
            }
            write_json(QUESTIONS_FILE, questions)
            return jsonify(questions[i])

    return jsonify({"error": "Question not found"}), 404


@app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
@require_admin
def admin_delete_question(qid):
    questions = read_json(QUESTIONS_FILE)
    new_list = [q for q in questions if q["id"] != qid]

    if len(new_list) == len(questions):
        return jsonify({"error": "Question not found"}), 404

    write_json(QUESTIONS_FILE, new_list)
    return jsonify({"message": "Deleted"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
