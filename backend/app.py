import csv
import io
import os
import json
import uuid
import secrets
import string
import re
import datetime
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-production")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"welcome_text": ""}
    return read_json(SETTINGS_FILE)


def write_settings(data):
    write_json(SETTINGS_FILE, data)


def find_user(users, user_id):
    return next((u for u in users if u["id"] == user_id), None)


def find_user_by_email(users, email):
    email = email.strip().lower()
    return next((u for u in users if u["username"].lower() == email), None)


EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,}$"
)


def is_valid_email(email):
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email))


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["username"],
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "is_admin": user["is_admin"],
    }


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def generate_password(length=8):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def user_has_results(user):
    return bool(user.get("results"))


def quiz_questions_safe():
    questions = read_json(QUESTIONS_FILE)
    return [
        {
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "time_limit": q["time_limit"],
            "image": q.get("image"),
        }
        for q in questions
    ]


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
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not first_name or not last_name or not email or not password:
        return jsonify({"error": "First name, last name, email, and password are required"}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    users = read_json(USERS_FILE)

    if any(u["username"].lower() == email for u in users):
        return jsonify({"error": "An account with this email already exists"}), 409

    is_admin = len(users) == 0  # first user becomes admin

    user = {
        "id": str(uuid.uuid4()),
        "first_name": first_name,
        "last_name": last_name,
        "username": email,
        "password_hash": hash_password(password),
        "is_admin": is_admin,
        "quiz_started": False,
        "quiz_started_at": None,
        "results": [],
    }
    users.append(user)
    write_json(USERS_FILE, users)

    return jsonify({"message": "Registered successfully", "is_admin": is_admin}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    users = read_json(USERS_FILE)
    user = find_user_by_email(users, email)

    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid email or password"}), 401

    payload = {
        "id": user["id"],
        "username": user["username"],
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "is_admin": user["is_admin"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "token": token,
        "user": public_user(user),
    })


# ---------------------------------------------------------------------------
# Quiz routes
# ---------------------------------------------------------------------------

@app.route("/api/quiz/status", methods=["GET"])
@require_auth
def get_quiz_status():
    settings = read_settings()
    users = read_json(USERS_FILE)
    user = find_user(users, request.current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    is_admin = bool(user.get("is_admin"))
    quiz_started = bool(user.get("quiz_started"))
    has_result = user_has_results(user)
    questions = read_json(QUESTIONS_FILE)

    return jsonify({
        "welcome_text": settings.get("welcome_text", ""),
        "quiz_started": quiz_started,
        "has_result": has_result,
        "can_take_quiz": is_admin or (not quiz_started and not has_result),
        "question_count": len(questions),
    })


@app.route("/api/quiz/start", methods=["POST"])
@require_auth
def start_quiz():
    users = read_json(USERS_FILE)
    user_id = request.current_user["id"]
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.get("is_admin") and (user.get("quiz_started") or user_has_results(user)):
        return jsonify({"error": "Quiz already started"}), 403

    questions = read_json(QUESTIONS_FILE)
    if not questions:
        return jsonify({"error": "No questions available"}), 400

    user["quiz_started"] = True
    user["quiz_started_at"] = datetime.datetime.utcnow().isoformat()
    write_json(USERS_FILE, users)

    return jsonify({"questions": quiz_questions_safe()})


@app.route("/api/quiz", methods=["GET"])
@require_auth
def get_quiz():
    users = read_json(USERS_FILE)
    user = find_user(users, request.current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.get("quiz_started"):
        return jsonify({"error": "Quiz not started"}), 403

    return jsonify(quiz_questions_safe())


@app.route("/api/quiz/submit", methods=["POST"])
@require_auth
def submit_quiz():
    data = request.get_json() or {}
    answers = data.get("answers", {})   # {str(question_id): option_index | null}
    time_taken = data.get("time_taken", 0)

    users = read_json(USERS_FILE)
    user_id = request.current_user["id"]
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.get("quiz_started"):
        return jsonify({"error": "Quiz not started"}), 403

    if not user.get("is_admin") and user_has_results(user):
        return jsonify({"error": "Quiz already submitted"}), 403

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
    user_id = request.current_user["id"]
    for u in users:
        if u["id"] == user_id:
            u["results"].append({
                "date": datetime.datetime.utcnow().isoformat(),
                "score": score,
                "total": len(questions),
                "time_taken": time_taken,
                "questions": [
                    {
                        "id": r["id"],
                        "is_correct": r["is_correct"],
                        "user_answer": r["user_answer"],
                    }
                    for r in results
                ],
            })
            # Admins may retake the quiz, so clear the in-progress flag.
            if u.get("is_admin"):
                u["quiz_started"] = False
                u["quiz_started_at"] = None
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


def _build_admin_results():
    questions = read_json(QUESTIONS_FILE)
    users = read_json(USERS_FILE)

    question_meta = [
        {"id": q["id"], "question": q["question"]}
        for q in questions
    ]

    participants = []
    for user in users:
        participants.append({
            "id": user["id"],
            "username": user["username"],
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "is_admin": bool(user.get("is_admin")),
            "quiz_started": bool(user.get("quiz_started")),
            "quiz_started_at": user.get("quiz_started_at"),
            "results": user.get("results", []),
        })

    return {"questions": question_meta, "participants": participants}


def _question_score(result, question_id):
    for q in result.get("questions", []):
        if q.get("id") == question_id:
            return 1 if q.get("is_correct") else 0
    return ""


@app.route("/api/admin/results", methods=["GET"])
@require_admin
def admin_get_results():
    return jsonify(_build_admin_results())


@app.route("/api/admin/results/export", methods=["GET"])
@require_admin
def admin_export_results():
    data = _build_admin_results()
    questions = data["questions"]

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["email", "first_name", "last_name", "attempt_date", "time_taken_seconds"]
    header.extend(f"Q{q['id']}" for q in questions)
    header.extend(["total_score", "total_questions"])
    writer.writerow(header)

    for participant in data["participants"]:
        for attempt in participant["results"]:
            row = [
                participant["username"],
                participant.get("first_name", ""),
                participant.get("last_name", ""),
                attempt.get("date", ""),
                attempt.get("time_taken", ""),
            ]
            row.extend(_question_score(attempt, q["id"]) for q in questions)
            row.extend([
                attempt.get("score", ""),
                attempt.get("total", ""),
            ])
            writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=quiz-results.csv"},
    )


@app.route("/api/admin/results", methods=["DELETE"])
@require_admin
def admin_delete_result():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    date = data.get("date")

    if not user_id or not date:
        return jsonify({"error": "user_id and date are required"}), 400

    users = read_json(USERS_FILE)
    found = False
    for user in users:
        if user["id"] != user_id:
            continue
        found = True

        if date == "__abandoned__":
            if not user.get("quiz_started") or user_has_results(user):
                return jsonify({"error": "No abandoned attempt found"}), 404
        else:
            before = len(user.get("results", []))
            user["results"] = [r for r in user.get("results", []) if r.get("date") != date]
            if len(user["results"]) == before:
                return jsonify({"error": "Result not found"}), 404

        user["quiz_started"] = False
        user["quiz_started_at"] = None
        break

    if not found:
        return jsonify({"error": "User not found"}), 404

    write_json(USERS_FILE, users)
    return jsonify({"message": "Deleted"})


@app.route("/api/admin/results/all", methods=["DELETE"])
@require_admin
def admin_delete_all_results():
    users = read_json(USERS_FILE)
    cleared = 0

    for user in users:
        if user.get("results") or user.get("quiz_started"):
            cleared += 1
        user["results"] = []
        user["quiz_started"] = False
        user["quiz_started_at"] = None

    write_json(USERS_FILE, users)
    return jsonify({"message": "All participant results deleted", "cleared": cleared})


@app.route("/api/admin/password", methods=["PUT"])
@require_admin
def admin_change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password are required"}), 400
    if len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    users = read_json(USERS_FILE)
    user = find_user(users, request.current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Current password is incorrect"}), 401

    user["password_hash"] = hash_password(new_password)
    write_json(USERS_FILE, users)
    return jsonify({"message": "Password updated"})


@app.route("/api/admin/users/<user_id>/password", methods=["PUT"])
@require_admin
def admin_reset_user_password(user_id):
    data = request.get_json() or {}
    new_password = (data.get("new_password") or "").strip()

    if new_password and len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    if not new_password:
        new_password = generate_password()

    users = read_json(USERS_FILE)
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.get("is_admin"):
        return jsonify({"error": "Use Change Password to update the admin account"}), 400

    user["password_hash"] = hash_password(new_password)
    write_json(USERS_FILE, users)
    return jsonify({
        "message": "Password reset",
        "username": user["username"],
        "password": new_password,
    })


@app.route("/api/admin/settings", methods=["GET"])
@require_admin
def admin_get_settings():
    return jsonify(read_settings())


@app.route("/api/admin/settings", methods=["PUT"])
@require_admin
def admin_update_settings():
    data = request.get_json() or {}
    welcome_text = data.get("welcome_text", "")
    if not isinstance(welcome_text, str):
        return jsonify({"error": "welcome_text must be a string"}), 400

    settings = {"welcome_text": welcome_text.strip()}
    write_settings(settings)
    return jsonify(settings)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
